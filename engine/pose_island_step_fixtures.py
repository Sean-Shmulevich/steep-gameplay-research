"""Synthetic rider-shaped fixtures for the composed island step.

Evidence: LINK_SOLVER.md, Composed island step; PHYSICS_SUBSTEP_ORDER.md,
section 5. Every record here is an authored synthetic fixture laid out in the
retained-record formats already recovered for the analysed build. Nothing is a
captured game payload. Masses, inertia, capsule placement, terrain profiles,
contact points, action objects and settings are invented test values; only the
capsule (half-height, radius) pairs come from the task brief and the world
settings defaults come from physics_substep_order.json.

The builder produces address-keyed regions. The same bytes are written into
the private native harness and copied into the independent model, so both
start from identical retained state.
"""
import math
import random
import struct
from .pose_context_init import initialize_pose_jobs

IMAGE_BASE = 0x140000000
BODY_VTABLE = IMAGE_BASE + 0x29C99A8      # constructor-selected body class
BOX_RESOURCE_VTABLE = IMAGE_BASE + 0x29C9AC8
CAPSULE_RESOURCE_VTABLE = IMAGE_BASE + 0x29C9B58
# Live reads (Phase 3, LINK_SOLVER.md "Composed island step on live substeps"):
SPHERE_RESOURCE_VTABLE = IMAGE_BASE + 0x29C9BE8  # rider spheres; slot 0x10 = 0x18c75a0
STATIC_BODY_VTABLE = IMAGE_BASE + 0x29C98C8      # static link endpoints (body layout)
BROADPHASE_TABLE = IMAGE_BASE + 0x29CA8A0        # dynamic-tree broadphase
SETTINGS_VTABLE = IMAGE_BASE + 0x29CA978         # live read: object at world+0x08
CALLBACK_OWNER_GLOBAL = IMAGE_BASE + 0x33365E0   # [global]+0x38 body-list callback
DISPATCHER_GLOBAL = IMAGE_BASE + 0x3336610       # dispatcher record, capacity at +0x10
ACTION_CALLBACK = IMAGE_BASE + 0x18B8C90         # lea at 0x18b9747

HEAP_BASE = 0x10000000
HEAP_SIZE = 0x700000
ARENA_SIZE = 0x10000
ARENA_POOL = 4

# Defaults equal the live settings read (PHYSICS_SUBSTEP_ORDER.md, Live settings):
# gravity (0,0,-9.81), mode 1, iterations 8/4, +0x21 = 1, +0x14 = 1, +0x20 = 0.
# Capsule (half-height, radius) pairs from the brief; placement is invented.
MAIN_CAPSULES = ((0.175, 0.16), (0.5625, 0.034375), (0.5625, 0.034375),
                 (0.6101562, 0.05546877))
RIDER_CAPSULES = ((0.08, 0.1), (0.25, 0.05), (0.25, 0.05))

DEFAULT_SETTINGS = dict(gravity=(0.0, 0.0, -9.81), quiet_check=1, ctx20=2.0,
                        ctx1c=-0.01, bypass=0, cache=1, mode=1, iterations=8,
                        secondary=4, ctx14=0.1, ctx18=0.2, linear=0.5,
                        angular=0.5, duration=0.5, island40=0.001,
                        island44=0.001)


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def pack_settings(values):
    """World settings block at world+0x08 (0x48 bytes), offsets per the map."""
    s = dict(DEFAULT_SETTINGS)
    s.update(values or {})
    raw = bytearray(0x48)
    struct.pack_into('<Q', raw, 0, SETTINGS_VTABLE)
    struct.pack_into('<3f', raw, 0x08, *s['gravity'])
    raw[0x14] = s['quiet_check'] & 0xff
    struct.pack_into('<ff', raw, 0x18, s['ctx20'], s['ctx1c'])
    raw[0x20] = s['bypass'] & 0xff
    raw[0x21] = s['cache'] & 0xff
    struct.pack_into('<IHH', raw, 0x24, s['mode'], s['iterations'], s['secondary'])
    struct.pack_into('<ff', raw, 0x2c, s['ctx14'], s['ctx18'])
    # Quiet thresholds as consumed by the validated poststep chain (worker 0x18e31b0
    # passes +0x34/+0x38/+0x3c; 0x18c0190 compares the timer against the first and
    # squared linear/angular speeds against the second/third). The Phase 1 JSON
    # labels +0x34 linear and +0x3c duration; that labelling disagrees with this use.
    struct.pack_into('<3f', raw, 0x34, s['duration'], s['linear'], s['angular'])
    struct.pack_into('<ff', raw, 0x40, s['island40'], s['island44'])
    return raw


class Region:
    """One retained record: bytes (bytearray) or a u64 pointer array (list)."""
    __slots__ = ('name', 'address', 'kind', 'data', 'category', 'compare')

    def __init__(self, name, address, kind, data, category, compare=True):
        self.name, self.address, self.kind = name, address, kind
        self.data, self.category, self.compare = data, category, compare

    @property
    def size(self):
        return len(self.data) * (8 if self.kind == 'u64' else 1)

    def raw(self):
        if self.kind == 'u64':
            return struct.pack('<%dQ' % len(self.data), *self.data)
        return bytes(self.data)


def _rotation(yaw, pitch, roll):
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    cr, sr = math.cos(roll), math.sin(roll)
    # Rows are images of local x/y/z (row-vector convention used by the body).
    m = [[cy*cp, sy*cp, -sp],
         [cy*sp*sr - sy*cr, sy*sp*sr + cy*cr, cp*sr],
         [cy*sp*cr + sy*sr, sy*sp*cr - cy*sr, cp*cr]]
    return [[f32(v) for v in row] for row in m]


def _apply(rows, local, translation):
    return [translation[j] + sum(rows[k][j]*local[k] for k in range(3)) for j in range(3)]


def _to_local(rows, world, translation):
    d = [world[j] - translation[j] for j in range(3)]
    return [f32(sum(rows[k][j]*d[j] for j in range(3))) for k in range(3)]


class IslandFixtureBuilder:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.cursor = HEAP_BASE
        self.regions = []
        self.by_name = {}
        self.code = []          # (address, bytes) native-only code stubs
        self.stubs = {}
        self.resources = {}
        self.profiles = {}
        self.tokens = {}
        self.notes = {}

    # --- allocation ---------------------------------------------------------------
    def alloc(self, size, align=0x40):
        self.cursor = (self.cursor + align - 1) & ~(align - 1)
        address = self.cursor
        self.cursor += size
        if self.cursor > HEAP_BASE + HEAP_SIZE - 0x100000:
            raise ValueError('Fixture heap exhausted')
        return address

    def add(self, name, size_or_data, category, *, kind='bytes', fill=None, compare=True, align=0x40):
        if kind == 'u64':
            data = list(size_or_data)
            address = self.alloc(len(data)*8, align)
        else:
            if isinstance(size_or_data, int):
                data = bytearray(self.rng.randbytes(size_or_data)) if fill == 'random' else bytearray(size_or_data)
            else:
                data = bytearray(size_or_data)
            address = self.alloc(len(data), align)
        region = Region(name, address, kind, data, category, compare)
        self.regions.append(region)
        self.by_name[name] = region
        return region

    def stub(self, name, code=b'\xc3'):
        address = self.alloc(len(code), 0x10)
        self.code.append((address, bytes(code)))
        self.stubs[name] = address
        return address


def build_island_fixture(case):
    """Return a dict describing one synthetic island-step fixture.

    case keys: seed, dt, settings (overrides), main_points (list of point counts
    per main terrain payload), rider (bool), rider_points, free_group, fixed_group,
    quiet_group, quiet_contact, sleeping_group, changed ('none'|'flagged'|'append'|
    'wake'), actions (node count), action_remove (bool), callback (bool),
    capacity (dispatcher worker capacity), second_rider (bool).
    """
    b = IslandFixtureBuilder(case['seed'])
    rng = b.rng

    # --- top-level objects ---------------------------------------------------------
    controller = b.add('controller', 0x78, 'controller', fill='random')
    world_head = b.add('world_head', 8, 'world', fill='random', align=0x40)
    settings = b.add('settings', pack_settings(case.get('settings')), 'settings', align=8)
    world_tail = b.add('world_tail', 0xa0, 'world', align=8)   # world+0x50..+0xf0
    assert settings.address == world_head.address + 8 and world_tail.address == world_head.address + 0x50
    world = world_head.address
    island = b.add('island', 0x4a0, 'island', fill='random')
    provider = b.add('provider', 0x40, 'provider', fill='random')
    stage = b.add('stage', 0x1040, 'stage', fill='random')
    if case.get('broadphase', True):
        # Dynamic-tree broadphase object with the original table: slot +0x98 = 0x199b590
        # (append 24-byte record to the +0xf8 vector), slot +0xa8 = 0x193fa10 (+0x49 flag).
        interface = b.add('interface', 0x100, 'interface', fill='random')
        struct.pack_into('<Q', interface.data, 0, BROADPHASE_TABLE)
        cap = 16
        vec = b.add('bp_vector', 0x20, 'bp_vector', fill='random')
        vdata = b.add('bp_vector_data', 24*cap, 'bp_vector', fill='random')
        used = rng.randrange(0, 4)
        struct.pack_into('<QII', vec.data, 0, vdata.address, used, cap)
        struct.pack_into('<Q', interface.data, 0xf8, vec.address)
    else:
        interface = b.add('interface', 0x10, 'interface', fill='random')
        interface_vt = b.add('interface_vt', 0xb0, 'vtable')
        struct.pack_into('<Q', interface.data, 0, interface_vt.address)
        struct.pack_into('<Q', interface_vt.data, 0x98, b.stub('publish'))
        struct.pack_into('<Q', interface_vt.data, 0xa8, b.stub('notify'))
    kind_stub = b.stub('pose_kind', b'\xb8\x02\x00\x00\x00\xc3')
    pose_vt = b.add('pose_vt', 0x20, 'vtable')
    struct.pack_into('<Q', pose_vt.data, 0x10, kind_stub)
    callback_owner = b.add('callback_owner', 0x40, 'callback_owner', fill='random')
    struct.pack_into('<Q', callback_owner.data, 0x38, b.stub('body_lists') if case.get('callback', True) else 0)
    dispatcher = b.add('dispatcher', 0x728, 'dispatcher')
    struct.pack_into('<I', dispatcher.data, 0x10, case.get('capacity', 1))
    c = controller.data
    for off, value in ((0x20, world), (0x28, interface.address), (0x30, island.address),
                       (0x38, provider.address), (0x40, stage.address)):
        struct.pack_into('<Q', c, off, value)
    struct.pack_into('<I', c, 0x48, 0)
    # Stage object: +8 controller, +0x18 world, empty deferred list, empty body tree.
    struct.pack_into('<Q', stage.data, 8, controller.address)
    struct.pack_into('<Q', stage.data, 0x18, world)
    struct.pack_into('<QII', stage.data, 0x1030, 0, 0, 0)
    # world+0x90 body tree 0: empty (root -1). world+0xd0 action tree.
    wt = world_tail.data
    def wset(off, fmt, *values):
        struct.pack_into(fmt, wt, off - 0x50, *values)
    wset(0x90, '<QIIIiI', 0, 0, 0, 0, -1, 0xffffffff)
    wset(0xb0, '<QIIIiI', 0, 0, 0, 0, -1, 0xffffffff)

    # --- island lists -----------------------------------------------------------
    special_a = b.add('group:special_a', 0xa8, 'group')
    special_b = b.add('group:static', 0xa8, 'group')
    active_arr = b.add('array:active', [0]*16, 'array', kind='u64')
    inactive_arr = b.add('array:inactive', [0]*16, 'array', kind='u64')
    batches = [b.add('batch:%d' % i, 16, 'batch', align=8) for i in range(8)]
    wake_arr = b.add('array:wake', [0]*32, 'array', kind='u64')
    sleep_arr = b.add('array:sleep', [0]*32, 'array', kind='u64')
    pending_arr = b.add('array:pending', [0]*16, 'array', kind='u64')
    # Batch records must be contiguous 16-byte slots.
    for i in range(1, 8):
        assert batches[i].address == batches[0].address + 16*i
    isl = island.data
    struct.pack_into('<QQ', isl, 0x408, special_a.address, special_b.address)
    struct.pack_into('<QII', isl, 0x438, batches[0].address, 0, 8)
    struct.pack_into('<I', isl, 0x448, 0)
    isl[0x44c] = 1
    struct.pack_into('<QII', isl, 0x470, wake_arr.address, 0, 32)
    struct.pack_into('<QII', isl, 0x480, sleep_arr.address, 0, 32)
    stale = rng.randrange(0, 3)   # stale pending entries are discarded by attach
    pending_arr.data[:stale] = [rng.randrange(1, 1 << 40) for _ in range(stale)]
    struct.pack_into('<QII', isl, 0x490, pending_arr.address, stale, 16)

    # --- profiles and resources -----------------------------------------------------
    def profile(name, f30, f40, f60, f64):
        r = b.add('profile:' + name, 0x70, 'profile')
        for off, v in ((0x30, f30), (0x40, f40), (0x60, f60), (0x64, f64)):
            struct.pack_into('<f', r.data, off, v)
        b.profiles[r.address] = dict(field30=f32(f30), field40=f32(f40), field60=f32(f60), field64=f32(f64))
        return r.address
    snow = profile('snow', 0.12 + rng.random()*0.3, 0.05*rng.random(), 1e14, 1.0)
    board = profile('board', 0.05 + rng.random()*0.1, 0.0, 1e14, 1.0)
    cloth = profile('cloth', 0.6, 0.1, 1e14, 1.0)

    def capsule(name, h, r, prof):
        res = b.add('resource:' + name, 0xc0, 'resource')
        struct.pack_into('<Q', res.data, 0, CAPSULE_RESOURCE_VTABLE)
        struct.pack_into('<Q', res.data, 0x20, prof)
        struct.pack_into('<H', res.data, 0x28, 0x8004)
        struct.pack_into('<ff', res.data, 0x40, h, r)
        b.resources[res.address] = dict(kind28=0x8004, default20=prof)
        return res.address

    def box(name, extents, prof):
        res = b.add('resource:' + name, 0xc0, 'resource')
        struct.pack_into('<Q', res.data, 0, BOX_RESOURCE_VTABLE)
        struct.pack_into('<Q', res.data, 0x20, prof)
        struct.pack_into('<H', res.data, 0x28, 0x8003)
        struct.pack_into('<3f', res.data, 0x40, *extents)
        b.resources[res.address] = dict(kind28=0x8003, default20=prof)
        return res.address

    # Terrain stand-in: only kind (7, no per-cell map) and default profile are read.
    terrain_res = b.add('resource:terrain', 0xc0, 'resource')
    struct.pack_into('<Q', terrain_res.data, 0x20, snow)
    struct.pack_into('<H', terrain_res.data, 0x28, 0x8007)
    b.resources[terrain_res.address] = dict(kind28=0x8007, default20=snow, mapb0=None, tablea0=0)

    # --- bodies ---------------------------------------------------------------------
    body_info = {}

    def body(name, *, group, index, rows, translation, linear, angular, inv_mass,
             inv_inertia, shapes, dynamic=True, fixed=False, timer=0.0, state53=0, flagsaa=0):
        rec = b.add('body:' + name, 0x200, 'body')
        meta = b.add('metadata:' + name, 0x60, 'metadata')
        raw = rec.data
        struct.pack_into('<Q', raw, 0, BODY_VTABLE)
        struct.pack_into('<Q', raw, 0x10, group)
        struct.pack_into('<I', raw, 0x1c, index)
        struct.pack_into('<f', raw, 0x28, timer)
        struct.pack_into('<Q', raw, 0x30, meta.address)
        for k in range(3):
            struct.pack_into('<3f', raw, 0x40 + 16*k, *rows[k])
        struct.pack_into('<3f', raw, 0x70, *translation)
        raw[0xaa] = flagsaa
        struct.pack_into('<f', raw, 0x124, inv_mass)
        struct.pack_into('<3f', raw, 0x128, *[f32(rng.uniform(-0.02, 0.02)) for _ in range(3)])
        # World inverse inertia R^T diag R.
        for i in range(3):
            row = [f32(sum(rows[k][i]*inv_inertia[k]*rows[k][j] for k in range(3))) for j in range(3)]
            struct.pack_into('<3f', raw, 0x170 + 16*i, *row)
        struct.pack_into('<3f', raw, 0x1a0, *map(f32, linear))
        struct.pack_into('<3f', raw, 0x1ac, *map(f32, angular))
        entries = b.add('entries:' + name, 72*max(1, len(shapes)), 'body_entries', align=8)
        for i, (resource, local) in enumerate(shapes):
            tr = b.add('transform:%s#%d' % (name, i), 64, 'transform', align=16)
            for k in range(3):
                struct.pack_into('<3f', tr.data, 16*k, *local[0][k])
            struct.pack_into('<3f', tr.data, 48, *local[1])
            struct.pack_into('<QQ', entries.data, 72*i + 16, resource, tr.address)
        struct.pack_into('<QH', raw, 0xb8, entries.address, len(shapes))
        m = meta.data
        struct.pack_into('<6f', m, 4, *([0.0]*6))
        struct.pack_into('<Q', m, 0x20, 0)
        struct.pack_into('<H', m, 0x50, 0x8000 if dynamic else 0)
        m[0x52] = 8 if fixed else 0
        m[0x53] = state53
        body_info[rec.address] = dict(name=name, rows=rows, translation=translation, links=[])
        return rec.address

    identity = [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]]
    axis_x = [[0, 1.0, 0], [1.0, 0, 0], [0, 0, -1.0]]     # local Y (capsule axis) -> body X
    axis_z = [[1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0]]     # local Y -> body Z
    terrain = body('terrain', group=special_b.address, index=0, rows=identity,
                   translation=[0.0, 0.0, 0.0], linear=[0, 0, 0], angular=[0, 0, 0],
                   inv_mass=0.0, inv_inertia=[0, 0, 0], shapes=[(terrain_res.address, (identity, [0, 0, 0]))],
                   dynamic=False, fixed=True)
    special_b_bodies = b.add('array:static_bodies', [terrain, 0, 0, 0], 'array', kind='u64')
    struct.pack_into('<QII', special_b.data, 0x10, special_b_bodies.address, 1, 4)

    # --- links, payloads, constraints ------------------------------------------------
    links = []

    def link(name, first, second, payloads, *, flags=1):
        raw = b.add('link:' + name, 0x90, 'link')
        entries = b.add('link_entries:' + name, 16*4, 'link_entries', align=8)
        struct.pack_into('<2Q', raw.data, 8, first, second)
        struct.pack_into('<QII', raw.data, 0x58, entries.address, len(payloads), 4)
        raw.data[0x84] = flags
        for i, p in enumerate(payloads):
            struct.pack_into('<QQ', entries.data, 16*i, rng.randrange(1, 1 << 32), p)
        links.append(raw.address)
        body_info[first]['links'].append(raw.address)
        body_info[second]['links'].append(raw.address)
        return raw.address

    def payload(name, first, shape_index, points):
        """Contact payload against flat terrain at z=0, normal from first to terrain."""
        p = b.add('payload:' + name, 0x120, 'payload')
        info = body_info[first]
        struct.pack_into('<I', p.data, 0x110, len(points))
        p.data[0x114] = 1
        for i, (wx, wy) in enumerate(points):
            depth = f32(-rng.uniform(0.002, 0.03))
            world_first = [wx, wy, depth]
            local_first = _to_local(info['rows'], world_first, info['translation'])
            base = 0x10 + 64*i
            struct.pack_into('<3f', p.data, base, *local_first)
            struct.pack_into('<3f', p.data, base + 0x10, f32(wx), f32(wy), 0.0)
            struct.pack_into('<3f', p.data, base + 0x20, 0.0, 0.0, -1.0)
            struct.pack_into('<I', p.data, base + 0x2c, rng.randrange(0, 1 << 16))
            struct.pack_into('<f', p.data, base + 0x30, depth)
            struct.pack_into('<f', p.data, base + 0x34, f32(rng.uniform(0, 2.0)))   # cache lane
            struct.pack_into('<HH', p.data, base + 0x38, shape_index, 0)
        return p.address

    def kind2(name, first, second, anchor_first, anchor_second, trial):
        r = b.add('pose:' + name, 0x1b0, 'pose')
        raw = r.data
        struct.pack_into('<Q', raw, 0, pose_vt.address)
        struct.pack_into('<2Q', raw, 8, first, second)
        raw[0x59] = trial & 1
        for offset in (0x80, 0xc0):
            for j in range(3):
                struct.pack_into('<3f', raw, offset + 16*j, *[float(j == k) for k in range(3)])
        struct.pack_into('<3f', raw, 0x70, *anchor_first)
        struct.pack_into('<3f', raw, 0xb0, *anchor_second)
        for i, offset in enumerate((0xf0, 0x104, 0x118, 0x12c, 0x140, 0x154)):
            state = (trial // (3 ** (i % 3))) % 3
            lo = f32(-rng.uniform(0.05, 0.5)); hi = f32(rng.uniform(0.05, 0.5))
            struct.pack_into('<I4f', raw, offset, state, lo, hi, 1e12 if trial % 4 else f32(rng.uniform(20, 400)), 1.0)
        for offset in (0x168, 0x174, 0x180):
            raw[offset] = (trial // 4) % 2
            raw[offset + 1] = 1
            struct.pack_into('<2f', raw, offset + 4, f32(rng.uniform(0.05, 0.4)), 1.0)
        struct.pack_into('<3I', raw, 0x190, 0xffffffff, 0xffffffff, 0xffffffff)
        return r.address

    groups = []           # (name, region) of groups listed active
    world_poses = []

    def group(name, bodies, link_tokens, pose_tokens, *, inactive=False):
        g = b.add('group:' + name, 0xa8, 'group')
        cap = 8
        barr = b.add('array:%s_bodies' % name, list(bodies) + [0]*(cap - len(bodies)), 'array', kind='u64')
        larr = b.add('array:%s_links' % name, list(link_tokens) + [0]*(cap - len(link_tokens)), 'array', kind='u64')
        parr = b.add('array:%s_poses' % name, list(pose_tokens) + [0]*(cap - len(pose_tokens)), 'array', kind='u64')
        struct.pack_into('<QII', g.data, 0x10, barr.address, len(bodies), cap)
        struct.pack_into('<QII', g.data, 0x40, larr.address, len(link_tokens), cap)
        struct.pack_into('<QII', g.data, 0x90, parr.address, len(pose_tokens), cap)
        g.data[0xa0] = 1 if inactive else 0
        for i, token in enumerate(link_tokens):
            struct.pack_into('<I', b.by_name['link:' + _name_of(b, token)].data, 0x80, i)
        return g

    def _place(group_region, tokens):
        for i, token in enumerate(tokens):
            struct.pack_into('<Q', b.by_name['body:' + body_info[token]['name']].data, 0x10, group_region.address)
            struct.pack_into('<I', b.by_name['body:' + body_info[token]['name']].data, 0x1c, i)

    trial = rng.randrange(0, 1 << 16)

    def rider_group(prefix, origin, speed_scale):
        yaw = rng.uniform(-math.pi, math.pi)
        rows = _rotation(yaw, rng.uniform(-0.25, 0.25), rng.uniform(-0.2, 0.2))
        t = [f32(origin[0]), f32(origin[1]), f32(0.95 + rng.uniform(-0.02, 0.02))]
        heading = [rows[0][0], rows[0][1], 0.0]
        lin = [heading[0]*speed_scale + rng.uniform(-1, 1), heading[1]*speed_scale + rng.uniform(-1, 1),
               rng.uniform(-1.5, 0.5)]
        ang = [rng.uniform(-1.2, 1.2) for _ in range(3)]
        shapes = []
        placements = [(axis_z, [0.0, 0.0, 0.55]), (axis_x, [0.0, 0.12, -0.9]),
                      (axis_x, [0.0, -0.12, -0.9]), (axis_x, [0.0, 0.0, -0.92])]
        for i, ((h, r), place) in enumerate(zip(MAIN_CAPSULES, placements)):
            shapes.append((capsule('%s_main%d' % (prefix, i), h, r, board if i else cloth), place))
        main = body(prefix + 'main', group=0, index=0, rows=rows, translation=t, linear=lin, angular=ang,
                    inv_mass=f32(1/rng.uniform(55, 95)), inv_inertia=[f32(1/rng.uniform(4, 9)), f32(1/rng.uniform(4, 9)),
                    f32(1/rng.uniform(1, 3))], shapes=shapes)
        members = [main]
        poses = []
        link_tokens = []
        board_pts = case.get('main_points', [2])
        for j, n in enumerate(board_pts):
            pts = []
            for _ in range(n):
                local = [rng.uniform(-0.7, 0.7), rng.uniform(-0.13, 0.13), -0.97]
                w = _apply(rows, local, t)
                pts.append((w[0], w[1]))
            shape_index = (1, 2, 3)[j % 3]
            p = payload('%smain_terrain%d' % (prefix, j), main, shape_index, pts)
            link_tokens.append(link('%smain_terrain%d' % (prefix, j), main, terrain, [p]))
        if case.get('rider', True):
            rt = [f32(t[j] + rows[2][j]*0.6) for j in range(3)]
            rshapes = []
            for i, ((h, r), place) in enumerate(zip(RIDER_CAPSULES, [(axis_z, [0, 0, 0.35]), (axis_x, [0, 0.2, 0.1]),
                                                                     (axis_x, [0, -0.2, 0.1])])):
                rshapes.append((capsule('%srider%d' % (prefix, i), h, r, cloth), place))
            rider = body(prefix + 'rider', group=0, index=1, rows=rows, translation=rt,
                         linear=[lin[k] + rng.uniform(-0.3, 0.3) for k in range(3)],
                         angular=[ang[k] + rng.uniform(-0.5, 0.5) for k in range(3)],
                         inv_mass=f32(1/rng.uniform(6, 14)), inv_inertia=[f32(1/rng.uniform(0.3, 0.9))]*3,
                         shapes=rshapes)
            members.append(rider)
            poses.append(kind2(prefix + 'spring', main, rider, [0.0, 0.0, 0.3], [0.0, 0.0, -0.3], trial))
            for j, n in enumerate(case.get('rider_points', [])):
                pts = [(_apply(rows, [rng.uniform(-0.3, 0.3), rng.uniform(-0.2, 0.2), 0.0], rt)[0],
                        _apply(rows, [0, rng.uniform(-0.2, 0.2), 0.0], rt)[1]) for _ in range(n)]
                p = payload('%srider_terrain%d' % (prefix, j), rider, j % 3, pts)
                link_tokens.append(link('%srider_terrain%d' % (prefix, j), rider, terrain, [p]))
        return members, link_tokens, poses

    def _name_of(builder, token):
        for r in builder.regions:
            if r.address == token and r.name.startswith('link:'):
                return r.name[5:]
        raise KeyError(token)

    active_groups = []
    members, link_tokens, poses = rider_group('', (rng.uniform(-50, 50), rng.uniform(-50, 50)), rng.uniform(4, 14))
    g_main = group('main', members, link_tokens, poses)
    _place(g_main, members)
    active_groups.append(g_main)
    world_poses += poses
    b.tokens['main'] = members[0]
    if len(members) > 1:
        b.tokens['rider'] = members[1]
    if case.get('second_rider'):
        members2, links2, poses2 = rider_group('b_', (rng.uniform(-50, 50), rng.uniform(-50, 50)), rng.uniform(1, 6))
        g2 = group('second', members2, links2, poses2)
        _place(g2, members2)
        active_groups.append(g2)
        world_poses += poses2

    def loose(name, *, fixed=False, quiet=False, contact=False, shapes_kind='capsule', inactive=False):
        rows = _rotation(rng.uniform(-3, 3), rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4))
        t = [f32(rng.uniform(-80, 80)), f32(rng.uniform(-80, 80)), f32(0.3 if (quiet or contact) else rng.uniform(1, 6))]
        if quiet:
            lin = [rng.uniform(-0.02, 0.02) for _ in range(3)]
            ang = [rng.uniform(-0.02, 0.02) for _ in range(3)]
        else:
            lin = [rng.uniform(-4, 4) for _ in range(3)]
            ang = [rng.uniform(-2, 2) for _ in range(3)]
        if shapes_kind == 'capsule':
            shp = [(capsule(name + '0', 0.2, 0.1, board), (axis_x, [0, 0, 0]))]
        else:
            shp = [(box(name + '0', (0.2, 0.15, 0.1), board), (identity, [0, 0, 0]))]
        token = body(name, group=0, index=0, rows=rows, translation=t, linear=[0, 0, 0] if fixed else lin,
                     angular=[0, 0, 0] if fixed else ang, inv_mass=0.0 if fixed else f32(1/rng.uniform(2, 20)),
                     inv_inertia=[0, 0, 0] if fixed else [f32(1/rng.uniform(0.05, 0.5))]*3, shapes=shp,
                     dynamic=not fixed, fixed=fixed,
                     timer=f32(0.5 - rng.uniform(0.0, 0.04)) if quiet else f32(rng.uniform(0, 0.3)),
                     state53=2 if inactive else 0, flagsaa=8 if (not fixed and rng.random() < 0.15) else 0)
        lks = []
        if contact:
            pts = [(_apply(rows, [rng.uniform(-0.2, 0.2), 0, -0.1], t)[0], _apply(rows, [0, rng.uniform(-0.1, 0.1), -0.1], t)[1])
                   for _ in range(rng.randrange(1, 3))]
            p = payload(name + '_terrain', token, 0, pts)
            lks.append(link(name + '_terrain', token, terrain, [p]))
        g = group(name, [token], lks, [], inactive=inactive)
        _place(g, [token])
        return token, g

    if case.get('free_group', True):
        active_groups.append(loose('free', shapes_kind='box' if rng.random() < 0.3 else 'capsule')[1])
    if case.get('fixed_group'):
        active_groups.append(loose('fixed', fixed=True)[1])
    if case.get('quiet_group'):
        active_groups.append(loose('quiet', quiet=True, contact=case.get('quiet_contact', True))[1])
    inactive_groups = []
    sleeper = None
    if case.get('sleeping_group'):
        sleeper, gs = loose('sleeper', quiet=True, contact=True, inactive=True)
        inactive_groups.append(gs)

    # Shuffle active order (batch ordering sorts by work afterwards).
    rng.shuffle(active_groups)
    for i, g in enumerate(active_groups):
        active_arr.data[i] = g.address
        struct.pack_into('<I', g.data, 0xc, i)
    for i, g in enumerate(inactive_groups):
        inactive_arr.data[i] = g.address
        struct.pack_into('<I', g.data, 0xc, i)
    struct.pack_into('<QII', isl, 0x418, active_arr.address, len(active_groups), 16)
    struct.pack_into('<QII', isl, 0x428, inactive_arr.address, len(inactive_groups), 16)

    # --- changed links (provider +0x28/+0x30) -------------------------------------
    changed_kind = case.get('changed', 'none')
    changed = []
    if changed_kind == 'flagged' and links:
        changed.append(links[0])
        b.by_name['link:' + _name_of(b, links[0])].data[0x84] |= 2
    elif changed_kind in ('append', 'wake'):
        target = sleeper if (changed_kind == 'wake' and sleeper) else b.tokens['main']
        info = body_info[target]
        pts = [(_apply(info['rows'], [rng.uniform(-0.3, 0.3), 0, -0.9], info['translation'])[0],
                _apply(info['rows'], [0, rng.uniform(-0.1, 0.1), -0.9], info['translation'])[1])
               for _ in range(rng.randrange(1, 4))]
        p = payload('changed', target, 0, pts)
        changed.append(link('changed', target, terrain, [p]))
    changed_arr = b.add('array:changed', changed + [0]*(4 - len(changed)), 'array', kind='u64')
    struct.pack_into('<QI', provider.data, 0x28, changed_arr.address, len(changed))

    # --- body link rings (circular; next at +0x20 for first endpoint, +0x30 second) ---
    for token, info in body_info.items():
        ring = info['links']
        rec = b.by_name['body:' + info['name']].data
        struct.pack_into('<Q', rec, 0x80, ring[0] if ring else 0)
        for i, lt in enumerate(ring):
            raw = b.by_name['link:' + _name_of(b, lt)].data
            first = struct.unpack_from('<Q', raw, 8)[0]
            nxt, prev = ring[(i + 1) % len(ring)], ring[(i - 1) % len(ring)]
            struct.pack_into('<QQ', raw, 0x20 if first == token else 0x30, nxt, prev)

    # --- world constraint list (C4 scans kinds) and empty command collections --------
    wlist = b.add('array:world_constraints', world_poses + [0]*(8 - len(world_poses)), 'array', kind='u64')
    wset(0x50, '<QI', 0, 0)
    wset(0x58, '<I', 0)
    wset(0x60, '<QI', wlist.address, len(world_poses))
    # Command constraint collections (C2): authored kind-4 records whose stored
    # callback is a stub; the callback output (six 64-byte commands + count) is
    # authored fixture data applied identically on both sides.
    command_outputs = {}
    for offset, count in zip((0x70, 0x80), case.get('commands', (0, 0))):
        tokens = []
        for i in range(count):
            r = b.add('command:%x_%d' % (offset, i), 0x200, 'command', fill='random')
            second = b.tokens.get('rider') if rng.random() < 0.7 else 0
            struct.pack_into('<2Q', r.data, 8, b.tokens['main'], second or 0)
            r.data[0x59] = rng.choice((0, 0, 1, 2))
            struct.pack_into('<Q', r.data, 0x1f8, b.stub('command_cb:%x_%d' % (offset, i)))
            command_outputs[r.address] = (rng.randbytes(384), rng.choice((0, 1, 3, 6, 7)))
            tokens.append(r.address)
        arr = b.add('array:commands_%x' % offset, tokens + [0]*(4 - len(tokens)), 'array', kind='u64')
        wset(offset, '<QI', arr.address, len(tokens))

    # --- action tree at world+0xd0 (authored action objects) ------------------------
    n_actions = case.get('actions', 0)
    action_effects = []
    if n_actions:
        nodes = b.add('action_nodes', 32*n_actions, 'action_nodes', align=8)
        remove = case.get('action_remove', False)
        for i in range(n_actions):
            obj = b.add('action:%d' % i, 0x20, 'action')
            vt = b.add('action_vt:%d' % i, 0x10, 'vtable')
            tgt = b.add('action_target:%d' % i, 0x40, 'action_target')
            tmeta = b.add('action_target_meta:%d' % i, 0x60, 'action_target')
            tmeta.data[0x52] = 1                  # gate bit0 set: callback interior skipped
            struct.pack_into('<Q', tmeta.data, 0x20, tmeta.address)
            struct.pack_into('<Q', tgt.data, 0x30, tmeta.address)
            struct.pack_into('<Q', vt.data, 0, b.stub('action_destroy:%d' % i))
            struct.pack_into('<Q', vt.data, 8, b.stub('action_update:%d' % i))
            struct.pack_into('<QQI', obj.data, 0, vt.address, tgt.address, 2 if (remove and i == n_actions - 1) else 1)
            # Valid red-black shape (byte +0xc: 1 red, 0 black) for 1..3 nodes,
            # in-order index order: n=2 root 0 + red right 1; n=3 root 1 + red 0/2.
            left, right, parent, red = {1: [(-1, -1, -1, 0)],
                                        2: [(-1, 1, -1, 0), (-1, -1, 0, 1)],
                                        3: [(-1, -1, 1, 1), (0, 2, -1, 0), (-1, -1, 1, 1)]}[n_actions][i]
            struct.pack_into('<iiiBBHQI', nodes.data, 32*i, left, right, parent, red, 0, 0, obj.address, i)
            # Authored effect: the action nudges the main body's linear velocity.
            action_effects.append(dict(index=i, entry=obj.address, body=b.tokens['main'], delta=[f32(rng.uniform(-0.2, 0.2)) for _ in range(3)]))
        if n_actions > 3:
            raise ValueError('Authored action trees cover one to three nodes')
        wset(0xd0, '<QIIIiI', nodes.address, n_actions, 0, 0, 1 if n_actions == 3 else 0, 0xffffffff)
    else:
        wset(0xd0, '<QIIIiI', 0, 0, 0, 0, -1, 0xffffffff)

    # --- solver scratch pool and random island job fields ---------------------------
    arenas = [b.add('arena:%d' % i, ARENA_SIZE, 'arena', fill='random') for i in range(ARENA_POOL)]
    initialize_pose_jobs(isl, context_token=island.address)
    return dict(case=case, regions=b.regions, code=b.code, stubs=b.stubs,
                resources=b.resources, profiles=b.profiles,
                tokens=dict(controller=controller.address, world=world, settings=settings.address,
                            island=island.address, provider=provider.address, stage=stage.address,
                            interface=interface.address, callback_owner=callback_owner.address,
                            dispatcher=dispatcher.address, main=b.tokens['main'],
                            arenas=[a.address for a in arenas]),
                action_effects=action_effects, command_outputs=command_outputs, dt=case['dt'])
