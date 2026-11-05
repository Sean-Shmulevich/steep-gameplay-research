"""Composed solver half of one physics substep (island step 0x18ae2c0).

Evidence: LINK_SOLVER.md, Composed island step; PHYSICS_SUBSTEP_ORDER.md,
section 1.3 rows C1..C10 and section 5. RVAs are anchors for the analysed build.

The composition is our design. It joins the already recovered modules in the
order the native entry runs them:

    18ae2c0(controller, dt):
        18b9710(controller, dt)                       # C1 phase 3 ... C9 phase 0
            C2  18b9830  command constraint preparation (two collections)
            C3  1959a70  action-tree walk on world+0xd0, callback 18b8c90
            C4  195b190 / ed2ea0 / 195c040  stage object at controller+0x40
            C5  18e2200  attach changed links (wake, migrate, merge, append)
            C6  publish island+0x490 pending links to broadphase slot +0x98
            C7..D10  18e2fb0  batches, dispatcher (capacity 1 runs inline),
                     worker, group step, free motion, poststep, transfer
            C9  broadphase slot +0xa8(null) if island+0x420 != 0
        C10a 18b74e0  [global 0x1433365e0]+0x38(controller, sleep list, wake list)
        C10b 18e1990  clear island+0x488 and +0x478

Every stage is an explicit, swappable service. bind_reconstructed_island_stages
binds the island-stage modules (C3 pose_island_action_tree, C4 begin/dt
pose_island_ccd_stage, C5 pose_island_attach, C6/C9 dynamic-tree broadphase
receivers). The C4 finish 0x195c040 has no reconstruction and is supplied, as a
``replay_effects`` service built from recorded native memory effects; any stage can
be run that way instead. The body-list callback is an external interface and is
always supplied. Nothing runs implicitly.

Live layout (LINK_SOLVER.md "Composed island step on live substeps"): IslandState
binds the inline small-buffer arrays (INLINE_SMALL_BUFFERS) as views into their
containing record and exposes damping (+0x1b8) and quiet-override (+0x1c0) records;
make_composed_batch_stage passes both through (damping_response stays supplied);
make_resource_bounds covers box, capsule and sphere (0x18c75a0). The integrated body
paths accept body class 0x29c99a8 only; static link endpoints (0x29c98c8) are rejected.
"""
import struct
from collections.abc import Mapping, Sequence
from .pose_update_stage import run_pose_update_stage, prepare_pose_constraint_collections
from .pose_batch_runtime import run_retained_pose_batch_pass
from .pose_context_init import bind_pose_jobs
from .pose_dispatch import pose_dispatch_serial_atomics
from .pose_group_worker import claim_pose_batch_serial
from .pose_poststep_runtime import make_integrated_pose_poststep
from .pose_link_payloads import clear_pose_link_contacts
from .pose_body_integration import integrate_pose_body
from .pose_scalar_trig import scalar_sin_cos
from .pose_box_resource_bounds import box_resource_bounds
from .pose_island_step_fixtures import (BOX_RESOURCE_VTABLE, CAPSULE_RESOURCE_VTABLE,
                                        SPHERE_RESOURCE_VTABLE, BODY_VTABLE, STATIC_BODY_VTABLE,
                                        CALLBACK_OWNER_GLOBAL, DISPATCHER_GLOBAL,
                                        ACTION_CALLBACK)
from reference.central_impulse import f32

# Boundary labels, in native execution order. 'poststep' boundaries repeat per
# group (before 0x19574f0) inside C7..D10.
BOUNDARIES = ('C2', 'C3', 'C4.begin', 'C4.scalar', 'C4.finish', 'C5', 'C6',
              'C7-D10', 'C9', 'C10a', 'C10b')
SUPPLIED_STAGES = ('action_tree', 'stage_begin', 'stage_finish', 'attach_links',
                   'publish_link', 'notify_active', 'body_list_callback')
MODELLED_STAGES = ('command_prepare', 'stage_scalar', 'batches', 'body_lists', 'clear_lists')


def _u32(raw, offset):
    return struct.unpack_from('<I', raw, offset)[0]


def _ptr(raw, offset):
    return struct.unpack_from('<Q', raw, offset)[0]


class RetainedRegions:
    """Address-keyed view over retained records (authored adapter).

    Each region is a bytearray or a list of uint64 pointer slots. Reads/writes
    may span adjacent regions; any byte outside every region is rejected.
    Regions may not overlap: storage that lives inside another record (inline
    small-buffer arrays) is a view into that record, see container().
    """
    def __init__(self):
        self.items = []

    def add(self, name, address, store):
        top = address + self.size(store)
        for base, other, held in self.items:
            if base < top and address < base + self.size(held):
                raise ValueError('Retained region %s overlaps %s; use a view for inline storage'
                                 % (name, other))
        self.items.append((address, name, store))
        self.items.sort(key=lambda item: item[0])

    def container(self, address, size):
        """(name, base, store) of the byte region wholly holding address+size, else None."""
        for base, name, store in self.items:
            if base <= address and address + size <= base + self.size(store):
                return None if isinstance(store, list) else (name, base, store)
        return None

    @staticmethod
    def size(store):
        return len(store) * 8 if isinstance(store, list) else len(store)

    @staticmethod
    def raw(store):
        if isinstance(store, list):
            return struct.pack('<%dQ' % len(store), *store)
        return bytes(store)

    def _covering(self, address, size):
        end = address + size
        out = []
        for base, name, store in self.items:
            top = base + self.size(store)
            if top <= address or base >= end:
                continue
            out.append((base, name, store))
        covered = sum(min(end, b + self.size(s)) - max(address, b) for b, _, s in out)
        if covered != size:
            raise KeyError('Address range outside retained regions: %#x+%#x' % (address, size))
        return out

    def read(self, address, size):
        out = bytearray(size)
        for base, _, store in self._covering(address, size):
            raw = self.raw(store)
            lo, hi = max(address, base), min(address + size, base + len(raw))
            out[lo - address:hi - address] = raw[lo - base:hi - base]
        return bytes(out)

    def write(self, address, data):
        for base, _, store in self._covering(address, len(data)):
            lo, hi = max(address, base), min(address + len(data), base + self.size(store))
            chunk = data[lo - address:hi - address]
            if isinstance(store, list):
                first, last = (lo - base) // 8, (hi - base - 1) // 8
                words = bytearray(struct.pack('<%dQ' % (last - first + 1), *store[first:last + 1]))
                words[lo - base - 8*first:hi - base - 8*first] = chunk
                store[first:last + 1] = struct.unpack('<%dQ' % (last - first + 1), words)
            else:
                store[lo - base:hi - base] = chunk

    def snapshot(self):
        return {name: self.raw(store) for _, name, store in self.items}


def diff_effects(before, after, addresses):
    """Byte runs that differ between two {name: bytes} snapshots -> [(address, bytes)]."""
    effects = []
    for name, old in before.items():
        new = after[name]
        if old == new:
            continue
        i = 0
        while i < len(old):
            if old[i] != new[i]:
                j = i
                while j < len(old) and old[j] != new[j]:
                    j += 1
                effects.append((addresses[name] + i, new[i:j]))
                i = j
            else:
                i += 1
    return effects


def replay_effects(regions, effects, *, log=None, name=None):
    """Supplied stage: record arguments and apply recorded memory effects.

    This is how stages without a reconstruction are composed: the native routine
    runs in the private harness, its writes are recorded, and the model applies
    exactly those writes at the same point in the order. It proves ordering and
    downstream consumption, not the stage's own behavior.
    """
    def service(*args):
        if log is not None:
            log.append((name, args))
        for address, data in effects:
            regions.write(address, data)
    return service


def native_crt_sort_prefix(slots, count, compare):
    """Element permutation of the CRT sort 0x1c8fd50 (generic element form).

    Same partition/small-range policy as engine.pose_contact_sort (validated on
    48-byte records); here elements are pointer slots and compare is the group
    work comparator. Unstable for equal keys exactly as the native sort.
    """
    def cmp(a, b):
        return compare(slots[a], slots[b])
    def swap(a, b):
        slots[a], slots[b] = slots[b], slots[a]
    pending = [(0, count - 1)] if count > 1 else []
    while pending:
        low, high = pending.pop()
        while low < high:
            size = high - low + 1
            if size <= 8:
                while high > low:
                    maximum = low
                    for p in range(low + 1, high + 1):
                        if cmp(p, maximum) > 0:
                            maximum = p
                    swap(maximum, high)
                    high -= 1
                break
            middle = low + size // 2
            if cmp(low, middle) > 0: swap(low, middle)
            if cmp(low, high) > 0: swap(low, high)
            if cmp(middle, high) > 0: swap(middle, high)
            left, right = low, high
            while True:
                if left < middle:
                    left += 1
                    while left < middle and cmp(left, middle) <= 0: left += 1
                if left >= middle:
                    left += 1
                    while left <= high and cmp(left, middle) <= 0: left += 1
                while True:
                    previous_right = right
                    right -= 1
                    if right <= middle or cmp(right, middle) <= 0: break
                if right < left: break
                swap(left, right)
                if middle == right: middle = left
            end = previous_right
            if end > middle:
                end -= 1
                while end > middle and cmp(end, middle) == 0: end -= 1
            if end <= middle:
                end -= 1
                while end > low and cmp(end, middle) == 0: end -= 1
            if end - low >= high - left:
                if low < end: pending.append((low, end))
                if left >= high: break
                low = left
            else:
                if left < high: pending.append((left, high))
                if low >= end: break
                high = end


def capsule_resource_bounds(half, radius, frame):
    """0x18c64a0 (capsule table 0x29c9b58 slot 0x10): axis row1 scaled by h.

    ext_j = |h*row1_j| + r; low = t - ext; high = ext + t (float32 each step).
    """
    h, r = f32(half), f32(radius)
    ext = [f32(abs(f32(h * f32(frame[1][j]))) + r) for j in range(3)]
    return [f32(f32(frame[3][j]) - ext[j]) for j in range(3)] + [f32(ext[j] + f32(frame[3][j])) for j in range(3)]


def sphere_resource_bounds(radius, frame):
    """0x18c75a0 (sphere table 0x29c9be8 slot 0x10): r = resource+0x40.

    low_j = t_j - r (subss t, r); high_j = r + t_j (addss r, t); float32 each.
    """
    r = f32(radius)
    t = [f32(frame[3][j]) for j in range(3)]
    return [f32(t[j] - r) for j in range(3)] + [f32(r + t[j]) for j in range(3)]


def make_resource_bounds(raw_resources):
    """Dispatch resource bounds by the retained resource vtable (box, capsule, sphere).

    Other resource classes are rejected rather than guessed.
    """
    def bounds(token, frame):
        raw = raw_resources[token]
        vt = _ptr(raw, 0)
        if vt == BOX_RESOURCE_VTABLE:
            return box_resource_bounds(struct.unpack_from('<3f', raw, 0x40), frame)
        if vt == CAPSULE_RESOURCE_VTABLE:
            return capsule_resource_bounds(*struct.unpack_from('<2f', raw, 0x40), frame)
        if vt == SPHERE_RESOURCE_VTABLE:
            return sphere_resource_bounds(struct.unpack_from('<f', raw, 0x40)[0], frame)
        raise ValueError('No reconstructed bounds for resource class %#x' % vt)
    return bounds


class InlinePointerArray(Sequence):
    """uint64 slots stored inside a containing retained record (authored view).

    Reads and writes go to the containing bytearray, so record snapshots and
    RegionMemory see the same bytes. Length is the fixed inline capacity.
    """
    def __init__(self, record, offset, capacity):
        if offset < 0 or offset + 8 * capacity > len(record):
            raise ValueError('Inline array outside its containing record')
        self.record, self.offset, self.capacity = record, offset, capacity

    def __len__(self):
        return self.capacity

    def _index(self, index):
        if index < 0:
            index += self.capacity
        if not 0 <= index < self.capacity:
            raise IndexError(index)
        return self.offset + 8 * index

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(self.capacity))]
        return struct.unpack_from('<Q', self.record, self._index(index))[0]

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            positions = range(*index.indices(self.capacity))
            values = list(value)
            if len(values) != len(positions):
                raise ValueError('Inline array slice assignment cannot resize')
            for i, v in zip(positions, values):
                self[i] = v
            return
        struct.pack_into('<Q', self.record, self._index(index), value)


class FloatRecords(Mapping):
    """address -> list of float32 decoded from retained byte records (authored view)."""
    def __init__(self, records, count):
        self.records, self.count = records, count

    def __getitem__(self, token):
        return list(struct.unpack_from('<%df' % self.count, self.records[token], 0))

    def __iter__(self):
        return iter(self.records)

    def __len__(self):
        return len(self.records)


# Inline small-buffer storage seen on live records (LINK_SOLVER.md "Composed island
# step on live substeps"): (record map, pointer field, count field and width,
# inline offset, inline capacity, element size, target). When the pointer field
# holds record+inline offset, the storage is a view into that record.
INLINE_SMALL_BUFFERS = (
    ('group', 0x10, (0x18, '<I'), 0x20, 4, 8, 'array'),         # group bodies
    ('group', 0x40, (0x48, '<I'), 0x50, 8, 8, 'array'),         # group links
    ('link', 0x58, (0x60, '<I'), 0x68, 1, 16, 'link_entries'),  # link contact entries
    ('body', 0xb8, (0xc0, '<H'), 0xc8, 1, 72, 'body_entries'),  # single body entry
)

# Live allocation spacing (Phase 3 dumps): adjacent link records 0x88 apart,
# resources 0x48, bodies 0x1d0. A dump builder must not read past these.
LIVE_RECORD_SPACING = dict(link=0x88, resource=0x48, body=0x1d0)


class IslandState:
    """Retained island-step records keyed by address token (authored container).

    Region categories 'damping' (16-byte records named by body+0x1b8) and
    'quiet_override' (12-byte records named by body+0x1c0) are exposed as
    damping_records / quiet_overrides (float lists). Inline small-buffer arrays
    (INLINE_SMALL_BUFFERS) are bound as views into their containing record when
    inline_buffers is true; add_inline_array/add_inline_entries bind others.
    Views are bound once: a pointer that later migrates is not followed.
    """
    def __init__(self, regions, *, resources, profiles, tokens, modes=None, globals_=None,
                 inline_buffers=True):
        self.regions = RetainedRegions()
        self.addresses = {}
        self.maps = {k: {} for k in ('body', 'metadata', 'group', 'link', 'payload', 'link_entries',
                                     'body_entries', 'transform', 'resource', 'pose', 'array',
                                     'batch', 'arena', 'profile', 'command', 'damping',
                                     'quiet_override')}
        self.named = {}
        for region in regions:
            data = list(region.data) if region.kind == 'u64' else bytearray(region.data)
            self.regions.add(region.name, region.address, data)
            self.addresses[region.name] = region.address
            self.named[region.name] = data
            if region.category in self.maps:
                self.maps[region.category][region.address] = data
        self.tokens = dict(tokens)
        self.resources = resources
        self.profiles = profiles
        self.modes = modes or {name: 0 for name in ('field30', 'field40', 'field60', 'field64')}
        self.globals = globals_ if globals_ is not None else {
            CALLBACK_OWNER_GLOBAL: tokens['callback_owner'], DISPATCHER_GLOBAL: tokens['dispatcher']}
        self.controller = self.named['controller']
        self.island = self.named['island']
        self.settings = self.named['settings']
        self.world_tail = self.named['world_tail']
        self.stage = self.named['stage']
        self.provider = self.named['provider']
        self.arrays = dict(self.maps['array'])
        binding = bind_pose_jobs(self.island, context_token=tokens['island'])
        self.jobs = binding['jobs']
        self.arrays[binding['table_token']] = binding['arguments']
        self.entry_arrays = {**self.maps['link_entries'], **self.maps['body_entries']}
        self.damping_records = FloatRecords(self.maps['damping'], 4)
        self.quiet_overrides = FloatRecords(self.maps['quiet_override'], 3)
        self.inline = []
        if inline_buffers:
            self.bind_inline_buffers()

    def add_inline_array(self, address, capacity):
        """Bind capacity u64 slots at address, inside one byte region, as an array view."""
        held = self.regions.container(address, 8 * capacity)
        if held is None:
            raise KeyError('No byte region holds inline array %#x+%#x' % (address, 8 * capacity))
        name, base, store = held
        view = InlinePointerArray(store, address - base, capacity)
        self.maps['array'][address] = view
        self.arrays[address] = view
        self.inline.append(('array', address, name))
        return view

    def add_inline_entries(self, address, size):
        """Bind size bytes at address, inside one byte region, as an entry-array view."""
        held = self.regions.container(address, size)
        if held is None:
            raise KeyError('No byte region holds inline entries %#x+%#x' % (address, size))
        name, base, store = held
        view = memoryview(store)[address - base:address - base + size]
        self.entry_arrays[address] = view
        self.inline.append(('entries', address, name))
        return view

    def bind_inline_buffers(self):
        """Bind every INLINE_SMALL_BUFFERS layout whose pointer names its own record."""
        for category, field, (count_at, count_fmt), offset, capacity, size, target in INLINE_SMALL_BUFFERS:
            for token, record in self.maps[category].items():
                if isinstance(record, list) or len(record) < field + 8:
                    continue
                if _ptr(record, field) != token + offset:
                    continue
                count = struct.unpack_from(count_fmt, record, count_at)[0]
                if count > capacity:
                    raise ValueError('%s %#x: %d inline entries exceed capacity %d'
                                     % (category, token, count, capacity))
                if target == 'array':
                    self.add_inline_array(token + offset, capacity)
                else:
                    self.add_inline_entries(token + offset, capacity * size)


def model_command_prepare(state, prepare_constraint=None):
    """C2 0x18b9830 via the recovered driver.

    prepare_constraint(token, reciprocal) is the per-constraint step; use
    make_command_preparation for the recovered 0x19445c0 wrapper. It is only
    required when a collection is nonempty.
    """
    world = state.tokens['world']
    def view(provider):
        if provider != world:
            raise ValueError('Provider identity changed')
        return state.world_tail
    def count(offset):
        return lambda provider: _u32(view(provider), offset - 0x50)
    def getter(offset):
        def get(provider, index):
            return state.arrays[_ptr(view(provider), offset - 0x50)][index]
        return get
    def prepare(constraint, reciprocal):
        if prepare_constraint is None:
            raise ValueError('Reached command constraint preparation requires a service')
        prepare_constraint(constraint, reciprocal)
    def stage(owner_token, scalar):
        prepare_pose_constraint_collections(owner_token, scalar=scalar,
            owners={state.tokens['controller']: state.controller},
            first_count=count(0x78), first_at=getter(0x70),
            second_count=count(0x88), second_at=getter(0x80), prepare_constraint=prepare)
    return stage


def make_command_preparation(state, invoke):
    """Per-constraint 0x19445c0 (pose_command_prepare); stored callback supplied.

    invoke(function, first, second, commands_view, count_view, reciprocal, mode,
    userdata) is the constraint's stored callback, an external service.
    """
    from .pose_command_prepare import prepare_pose_command_constraint
    def prepare(token, reciprocal):
        prepare_pose_command_constraint(state.maps['command'][token], reciprocal=reciprocal,
            bodies=state.maps['body'], metadata=state.maps['metadata'], invoke=invoke)
    return prepare


def model_stage_scalar(state):
    """C4 0x0ed2ea0: stage+0x10 = float32 dt."""
    def stage(stage_token, scalar):
        if stage_token != state.tokens['stage']:
            raise ValueError('Unexpected stage object')
        struct.pack_into('<f', state.stage, 0x10, scalar)
    return stage


def model_clear_lists(state):
    """C10b 0x18e1990: island+0x488 = island+0x478 = 0."""
    def stage(island_token):
        if island_token != state.tokens['island']:
            raise ValueError('Unexpected island context')
        struct.pack_into('<I', state.island, 0x488, 0)
        struct.pack_into('<I', state.island, 0x478, 0)
    return stage


def model_body_lists(state, callback):
    """C10a 0x18b74e0: call [owner+0x38](controller, sleep, n, wake, n) if nonnull."""
    def stage(owner_token, controller, sleep, sleep_count, wake, wake_count):
        owner = state.regions.read(owner_token + 0x38, 8)
        function = struct.unpack('<Q', owner)[0]
        if function:
            callback(function, controller, sleep, sleep_count, wake, wake_count)
    return stage


def _require_body_class(body, token):
    """The composed poststep/update bind body class 0x29c99a8 only.

    Static link endpoints use 0x29c98c8, whose slots 0x10..0x28 are `ret 0`; any
    other class reaching the integrated paths is rejected rather than guessed.
    """
    vt = _ptr(body, 0)
    if vt != BODY_VTABLE:
        kind = ' (static link-endpoint class, slots 0x10..0x28 are ret)' if vt == STATIC_BODY_VTABLE else ''
        raise ValueError('Body %#x class %#x%s reached the integrated body path; only %#x is bound'
                         % (token, vt, kind, BODY_VTABLE))


def make_composed_batch_stage(state, *, atan2, allocate, release_buffer, release_payload,
                              get_kind, half_angle_trig=scalar_sin_cos, poststep_wrapper=None,
                              settings_override=None, observe=None, sort_prefix=None,
                              damping_records=None, damping_response=None, quiet_overrides=None,
                              resource_bounds=None):
    """C7..D10: batches 0x18e2fb0 through the recovered retained modules.

    Composes run_retained_pose_batch_pass (order, batches, dispatcher, worker
    thunk, transfer) with the retained numerical worker, integrated poststep,
    contact retirement, constructor-selected body integration and box/capsule/
    sphere bounds. allocate/release_buffer/release_payload/atan2 are supplied
    services.

    damping_records (token -> 4 floats, body+0x1b8) and quiet_overrides (token ->
    3 floats, body+0x1c0) default to the state's 'damping'/'quiet_override'
    regions when it has any; otherwise None (reaching them then raises).
    damping_response(base, s) -> 4 multipliers is the damping library 0x1c453d0,
    always a supplied service. resource_bounds defaults to make_resource_bounds.
    """
    raw_resources = state.maps['resource']
    bodies, metadata, links = state.maps['body'], state.maps['metadata'], state.maps['link']
    if damping_records is None and state.maps['damping']:
        damping_records = state.damping_records
    if quiet_overrides is None and state.maps['quiet_override']:
        quiet_overrides = state.quiet_overrides
    def clear_link(token):
        clear_pose_link_contacts(links[token], entry_arrays=state.entry_arrays, release=release_payload)
    poststep = make_integrated_pose_poststep(groups=state.maps['group'], arrays=state.arrays,
        bodies=bodies, metadata=metadata, links=links, clear_link=clear_link,
        entry_arrays=state.entry_arrays, transforms=state.maps['transform'],
        resource_bounds=resource_bounds or make_resource_bounds(raw_resources),
        half_angle_trig=half_angle_trig, quiet_overrides=quiet_overrides)
    checked = poststep
    def poststep(group_token, *args):
        raw_group = state.maps['group'][group_token]
        start, count = struct.unpack_from('<QI', raw_group, 0x10)
        for token in (state.arrays[start][:count] if count else []):
            _require_body_class(bodies[token], token)
        return checked(group_token, *args)
    def update_body(token, body, s):
        _require_body_class(body, token)
        return integrate_pose_body(body, s, half_angle_trig=half_angle_trig)
    if poststep_wrapper is not None:
        poststep = poststep_wrapper(poststep)
    if observe is not None:
        inner = poststep
        def poststep(group_token, *args):
            observe('poststep', group_token)
            return inner(group_token, *args)
    def run(context_token, scalar, settings_token):
        if context_token != state.tokens['island'] or settings_token != state.tokens['settings']:
            raise ValueError('Unexpected island or settings identity')
        record = state.named['dispatcher']
        if state.globals[DISPATCHER_GLOBAL] != state.tokens['dispatcher']:
            raise ValueError('Dispatcher global identity changed')
        settings = settings_override(state.settings) if settings_override else state.settings
        cas, add = pose_dispatch_serial_atomics(record)
        def unexpected(*_):
            raise ValueError('Multi-worker dispatcher path reached; capacity 1 expected')
        worker_services = dict(contexts={state.tokens['island']: state.island},
            batches=state.maps['batch'], arrays=state.arrays, groups=state.maps['group'],
            bodies=bodies, metadata=metadata, settings={settings_token: settings}, links=links,
            entry_arrays=state.entry_arrays, constraints=state.maps['pose'], get_kind=get_kind,
            payloads=state.maps['payload'], resources=state.resources, profiles=state.profiles,
            modes=state.modes, buffers=state.maps['arena'], allocate=allocate, release=release_buffer,
            claim=lambda _: claim_pose_batch_serial(state.island), poststep=poststep, atan2=atan2,
            damping_records=damping_records, damping_response=damping_response,
            update_body=update_body)
        run_retained_pose_batch_pass(context_token, dispatcher=record, scalar=scalar,
            settings_token=settings_token, worker_callback_token=0x1418e3340, jobs=state.jobs,
            worker_services=worker_services,
            dispatch_services=dict(atomic_compare_exchange=cas, atomic_add=add, enqueue=unexpected,
                                   take=unexpected, notify=unexpected, wait=unexpected),
            sort_prefix=sort_prefix or native_crt_sort_prefix,
            grow_batches=unexpected, grow_lists=unexpected)
    return run


def run_pose_island_step(state, *, dt, stages, observe=None):
    """Run 0x18ae2c0(controller, dt) over retained state with explicit stages.

    stages must contain every name in SUPPLIED_STAGES and MODELLED_STAGES (use
    default_island_stages for the modelled ones). observe(label, extra) is called
    at each boundary in BOUNDARIES order (and per group before poststep).

    Stage signatures (tokens are retained-record addresses):
      command_prepare(controller, dt)            C2  0x18b9830
      action_tree(world+0xd0, dt, 0x1418b8c90)    C3  0x1959a70
      stage_begin(stage) / stage_finish(stage)   C4  0x195b190 / 0x195c040
      stage_scalar(stage, dt)                    C4  0x0ed2ea0
      attach_links(island, array, count)         C5  0x18e2200 (provider+0x28/+0x30)
      publish_link(interface, link+8 or 0)       C6  broadphase slot +0x98
      batches(island, dt, world+8)               C7..D10 0x18e2fb0
      notify_active(interface, 0)                C9  broadphase slot +0xa8
      body_lists(owner, controller, sleep, n, wake, n)   C10a 0x18b74e0
      body_list_callback(function, controller, sleep, n, wake, n)  [owner+0x38]
      clear_lists(island)                        C10b 0x18e1990
    A later reconstruction of C3/C4/C5 replaces the replay service by passing
    its own callable under the same name; nothing else changes.
    """
    missing = [name for name in SUPPLIED_STAGES + MODELLED_STAGES if name not in stages]
    if missing:
        raise ValueError('Missing island-step stages: %s' % ', '.join(missing))
    note = observe or (lambda label, extra=None: None)
    def at(label, function, result=None):
        def call(*args):
            value = function(*args)
            note(label, None)
            return value if result is None else result
        return call
    controller_token = state.tokens['controller']
    world = state.tokens['world']
    def get_body_source(provider):              # 0x11fd350: world+0xd0
        return provider + 0xd0
    def get_settings(provider):                 # 0x12af2d0: world+8 (after the C6 loop)
        note('C6', None)
        return provider + 8
    run_pose_update_stage(controller_token, scalar=f32(dt),
        owners={controller_token: state.controller},
        contexts={state.tokens['island']: state.island},
        collections={state.tokens['provider']: state.provider}, arrays=state.arrays,
        prepare=at('C2', stages['command_prepare']), get_body_source=get_body_source,
        update_bodies=at('C3', stages['action_tree']), body_update_callback=ACTION_CALLBACK,
        begin_contacts=at('C4.begin', stages['stage_begin']),
        update_contacts=at('C4.scalar', stages['stage_scalar']),
        finish_contacts=at('C4.finish', stages['stage_finish']),
        attach_links=at('C5', stages['attach_links']), publish_link=stages['publish_link'],
        get_settings=get_settings, run_batches=at('C7-D10', stages['batches']),
        notify_active=stages['notify_active'])
    note('C9', None)
    island = state.island
    stages['body_lists'](state.globals[CALLBACK_OWNER_GLOBAL], controller_token,
                         _ptr(island, 0x480), _u32(island, 0x488), _ptr(island, 0x470), _u32(island, 0x478))
    note('C10a', None)
    stages['clear_lists'](_ptr(state.controller, 0x30))
    note('C10b', None)


class RegionMemory:
    """PoseFlatMemory-like adapter over RetainedRegions (authored).

    Lets the flat-memory island-stage modules (pose_island_action_tree,
    pose_island_ccd_stage, pose_island_attach) run on the same retained records as
    the dict-based solver modules. view() is only available inside one byte region.
    """
    def __init__(self, regions):
        self.regions = regions

    def get(self, fmt, address):
        return struct.unpack(fmt, self.regions.read(address, struct.calcsize(fmt)))[0]

    def put(self, fmt, address, value):
        self.regions.write(address, struct.pack(fmt, value))

    def view(self, address, size):
        for base, name, store in self.regions.items:
            if base <= address and address + size <= base + RetainedRegions.size(store):
                if isinstance(store, list):
                    raise KeyError('No byte view of pointer-array region %s' % name)
                return memoryview(store)[address - base:address - base + size]
        raise KeyError('No single region holds %#x+%#x' % (address, size))

    def q(self, address): return self.get('<Q', address)
    def d(self, address): return self.get('<I', address)
    def i(self, address): return self.get('<i', address)
    def w(self, address): return self.get('<H', address)
    def b(self, address): return self.get('<B', address)
    def set_q(self, address, value): self.put('<Q', address, value & 0xFFFFFFFFFFFFFFFF)
    def set_d(self, address, value): self.put('<I', address, value & 0xFFFFFFFF)
    def set_b(self, address, value): self.put('<B', address, value & 0xFF)


def _unreached(name):
    def service(*args):
        raise ValueError('Reached supplied service %s, not provided for this composition' % name)
    return service


BROADPHASE_TABLE = 0x1429CA8A0


def bind_reconstructed_island_stages(state, *, action_update, action_destroy, constraint_kind,
                                     services=None, log=None):
    """Bind the reconstructed island-stage modules as C3/C4-begin/C5/C6/C9 services.

    C3  pose_island_action_tree.walk_pose_action_tree + wake_action_body (0x1959a70,
        0x18b8c90); entry update (+8) and destructor (slot 0) stay supplied
        (action_update(entry, dt), action_destroy(entry, flag)).
    C4  pose_island_ccd_stage.begin_swept_stage (0x195b190) and store_stage_dt
        (0x0ed2ea0); constraint_kind(token) is the constraint kind virtual (+0x10).
        The finish 0x195c040 is not reconstructed and is not bound here.
    C5  pose_island_attach.bind_island_attach (0x18e2200).
    C6/C9 broadphase receivers append_broadphase_pair (+0x98 = 0x199b590) and
        mark_broadphase_active (+0xa8 = 0x193fa10) when the interface vtable is
        the dynamic-tree table 0x29ca8a0; otherwise services['publish_link'] /
        services['notify_active'] are required.
    services may supply the reached callee services the modules require: enter,
    leave, transition (callback controller wrapper), grow_stage, remove_cross,
    remove_local, destroy_swept, remove_body, grow_bodies, grow_links, grow_arrays,
    allocator, destroy_group, grow_pairs. Any reached but unsupplied one raises.
    log, when given, receives (stage name, args) at each stage entry.
    """
    from .pose_island_action_tree import walk_pose_action_tree, wake_action_body
    from .pose_island_ccd_stage import begin_swept_stage, store_stage_dt
    from .pose_island_attach import (bind_island_attach, append_broadphase_pair,
                                     mark_broadphase_active)
    mem = RegionMemory(state.regions)
    svc = {name: _unreached(name) for name in (
        'enter', 'leave', 'transition', 'grow_stage', 'remove_cross', 'remove_local',
        'destroy_swept', 'remove_body', 'grow_bodies', 'grow_links', 'grow_arrays',
        'destroy_group', 'grow_pairs', 'publish_link', 'notify_active')}
    svc.update(services or {})
    class _NoAllocator:
        allocate = reallocate = release = staticmethod(_unreached('allocator'))
    allocator = svc.pop('allocator', _NoAllocator())
    note = (lambda name, args: log.append((name, args))) if log is not None else (lambda *a: None)
    attach = bind_island_attach(mem, remove_body=svc['remove_body'], grow_bodies=svc['grow_bodies'],
        grow_links=svc['grow_links'], grow_arrays=svc['grow_arrays'] if 'grow_arrays' in (services or {}) else None,
        allocator=allocator, destroy_group=svc['destroy_group'])

    def action_tree(source, dt, callback):
        note('action_tree', (source, dt, callback))
        if callback != ACTION_CALLBACK:
            raise ValueError('Unexpected body callback identity')
        walk_pose_action_tree(mem, source, dt, update=action_update, destroy=action_destroy,
            callback=lambda body: wake_action_body(mem, body, enter=svc['enter'], leave=svc['leave'],
                                                   transition=svc['transition']))

    def stage_begin(stage):
        note('stage_begin', (stage,))
        begin_swept_stage(mem, stage, kind=constraint_kind, grow=svc['grow_stage'],
                          remove_cross=svc['remove_cross'], remove_local=svc['remove_local'],
                          destroy=svc['destroy_swept'])

    def stage_scalar(stage, dt):
        store_stage_dt(mem, stage, dt)

    def attach_links(context, links, count):
        note('attach_links', (context, links, count))
        attach(context, links, count)

    def publish_link(interface, record):
        note('publish_link', (interface, record))
        if mem.q(interface) == BROADPHASE_TABLE:
            append_broadphase_pair(mem, interface, record, grow=svc['grow_pairs'])
        else:
            svc['publish_link'](interface, record)

    def notify_active(interface, argument):
        note('notify_active', (interface, argument))
        if mem.q(interface) == BROADPHASE_TABLE:
            mark_broadphase_active(mem, interface, argument)
        else:
            svc['notify_active'](interface, argument)

    return dict(action_tree=action_tree, stage_begin=stage_begin, stage_scalar=stage_scalar,
                attach_links=attach_links, publish_link=publish_link, notify_active=notify_active)


def default_island_stages(state, *, batch_stage, body_list_callback, prepare_constraint=None):
    """Modelled stage defaults; supplied stages must still be added by the caller."""
    return dict(command_prepare=model_command_prepare(state, prepare_constraint),
                stage_scalar=model_stage_scalar(state), batches=batch_stage,
                body_lists=model_body_lists(state, body_list_callback),
                body_list_callback=body_list_callback, clear_lists=model_clear_lists(state))
