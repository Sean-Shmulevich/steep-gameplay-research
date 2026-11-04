"""Byte-model adapter for the recovered ordinary-group processing routine (18e2de0).

Evidence: CENTRAL_IMPULSE.md, Ordinary-group processing and retirement; the offsets
below were read from the disassembly of RVA 0x18e2de0..0x18e2fa1 and match the native
harness analysis/command-executor-audit/check_pose_group_process.py (which writes the
same fields into emulated memory). Offsets are evidence anchors, not portable fields.

Established offsets (all in RVA 0x18e2de0 unless noted):
  group+0x00  qword  vtable; slot0 is called as (group, 1) = destroy        (0x1418e2e08..e15)
  group+0x10  qword  pointer to the body-token qword array                   (0x1418e2e28, e2ee1)
  group+0x18  uint32 body count, read right after finalize 18e11b0           (0x1418e2df2)
  context+0x410 qword  group410: destination group token, reloaded after
              eligibility/removal                                            (0x1418e2e5b, e2eff)
  body+0x30   qword  pointer to metadata record                              (0x1418e2e2f, e2ee9)
  metadata+0x52 byte flags8; bit3 gates single-body transfer and per-body
              destination eligibility                                        (0x1418e2e33, e2eed)
Unrelated to this routine (do not confuse): group+0x40/+0x48 is the *link* array used by
18e28d0/19581c0; +0xa0/+0xa1 are rebuild-stage flags (cleared by the rebuild before the call).

UNRESOLVED: the internals of every service (finalize 18e11b0, eligible 18e1dd0, remove_body
957fc0, append_body 19573c0, prepare 18e1b10, acquire 18e19c0, migrate 1957720, remove_group
18e2660, release 18c8f50, allocate 18c9140, destroy). Which bytes they write beyond group+0x18
and context+0x410 is not established; they are caller-supplied and receive tokens only.
The temporary destination descriptor ({pointer,count} on the native stack) is not
byte-addressable memory here; it stays a dict(slots=QwordArray, count=int) as in the
dict-model service interface. Tokens are map keys standing in for native pointers.
"""
import struct
from collections.abc import MutableMapping, MutableSequence, Mapping

from .pose_group_process import process_pose_group

GROUP_BODY_ARRAY = 0x10        # qword pointer to body-token array
GROUP_BODY_COUNT = 0x18        # uint32
CONTEXT_GROUP410 = 0x410       # qword
BODY_METADATA = 0x30           # qword pointer to metadata
METADATA_FLAGS8 = 0x52         # byte


class QwordArray(MutableSequence):
    """Little-endian qword sequence over a writable byte buffer (indices, slices)."""

    def __init__(self, buffer):
        self.buffer = buffer

    def __len__(self):
        return len(self.buffer) // 8

    def _index(self, i):
        if i < 0:
            i += len(self)
        if not 0 <= i < len(self):
            raise IndexError(i)
        return i * 8

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [self[k] for k in range(*i.indices(len(self)))]
        return struct.unpack_from('<Q', self.buffer, self._index(i))[0]

    def __setitem__(self, i, value):
        if isinstance(i, slice):
            keys = range(*i.indices(len(self)))
            values = list(value)
            if len(values) != len(keys):
                raise ValueError('Fixed-size storage: slice length must match')
            for k, v in zip(keys, values):
                self[k] = v
            return
        struct.pack_into('<Q', self.buffer, self._index(i), value)

    def __delitem__(self, i):
        raise TypeError('Fixed-size storage')

    def insert(self, i, value):
        raise TypeError('Fixed-size storage')


class _ContextView(MutableMapping):
    def __init__(self, context):
        self.context = context

    def __getitem__(self, key):
        if key != 'group410':
            raise KeyError(key)
        return struct.unpack_from('<Q', self.context, CONTEXT_GROUP410)[0]

    def __setitem__(self, key, value):
        if key != 'group410':
            raise KeyError(key)
        struct.pack_into('<Q', self.context, CONTEXT_GROUP410, value)

    def __delitem__(self, key):
        raise TypeError

    def __iter__(self):
        return iter(('group410',))

    def __len__(self):
        return 1


class _GroupView(MutableMapping):
    def __init__(self, token, group, slot_arrays):
        self.token, self.group, self.slot_arrays = token, group, slot_arrays

    def __getitem__(self, key):
        if key == 'token':
            return self.token
        if key == 'count':
            return struct.unpack_from('<I', self.group, GROUP_BODY_COUNT)[0]
        if key == 'slots':
            array = self.slot_arrays[struct.unpack_from('<Q', self.group, GROUP_BODY_ARRAY)[0]]
            return QwordArray(array)
        raise KeyError(key)

    def __setitem__(self, key, value):
        if key != 'count':
            raise KeyError(key)
        struct.pack_into('<I', self.group, GROUP_BODY_COUNT, value & 0xffffffff)

    def __delitem__(self, key):
        raise TypeError

    def __iter__(self):
        return iter(('token', 'count', 'slots'))

    def __len__(self):
        return 3


class _Bodies(Mapping):
    """body token -> dict(metadata=dict(flags8=byte)) read lazily from bytes."""

    def __init__(self, bodies, metadata):
        self.bodies, self.metadata = bodies, metadata

    def __getitem__(self, token):
        body = self.bodies[token]
        meta = self.metadata[struct.unpack_from('<Q', body, BODY_METADATA)[0]]
        return dict(metadata=dict(flags8=meta[METADATA_FLAGS8]))

    def __iter__(self):
        return iter(self.bodies)

    def __len__(self):
        return len(self.bodies)


def process_pose_group_bytes(context, group_token, *, contexts, groups, bodies,
                             metadata, slot_arrays, finalize, eligible, remove_body,
                             append_body, allocate, prepare, acquire_group, migrate,
                             release, remove_group, destroy):
    """Run 18e2de0 on byte-model state; returns the bool of process_pose_group.

    contexts/groups/bodies/metadata map tokens to writable bytearrays; slot_arrays maps
    the group+0x10 pointer to the writable bytearray of qword body tokens. All reads and
    writes of group+0x18 (count), context+0x410 and the destination storage go to bytes;
    no state is copied, so there is nothing to write back. Services receive tokens:
      finalize(context, group)            eligible(context, body) -> int
      remove_body(group, body)            append_body(group410_token, body)
      allocate(nbytes) -> bytearray       prepare(context, group, descriptor) -> int
      acquire_group(context) -> token     migrate(group, descriptor)
      release(storage)                    remove_group(context, group)
      destroy(group, argument)
    descriptor is dict(slots=QwordArray, count=int). allocate must return at least nbytes.
    """
    ctx = contexts[context]
    group = groups[group_token]
    view = _GroupView(group_token, group, slot_arrays)

    def alloc(nbytes):
        buffer = allocate(nbytes)
        if len(buffer) < nbytes:
            raise ValueError('allocate returned less than the requested bytes')
        return QwordArray(buffer)

    return process_pose_group(
        _ContextView(ctx), view,
        bodies=_BodyTokens(_Bodies(bodies, metadata)),
        finalize=lambda c, g: finalize(context, group_token),
        eligible=lambda c, b: eligible(context, b['token']),
        remove_body=lambda g, b: remove_body(group_token, b['token']),
        append_body=lambda dest, b: append_body(dest, b['token']),
        allocate=alloc,
        prepare=lambda c, g, d: prepare(context, group_token, d),
        acquire_group=lambda c: acquire_group(context),
        migrate=lambda g, d: migrate(group_token, d),
        release=release,
        remove_group=lambda c, g: remove_group(context, group_token),
        destroy=lambda g, a: destroy(group_token, a))


class _BodyTokens(Mapping):
    """Adds the body token to the lazily-read body record."""

    def __init__(self, inner):
        self.inner = inner

    def __getitem__(self, token):
        body = self.inner[token]
        body['token'] = token
        return body

    def __iter__(self):
        return iter(self.inner)

    def __len__(self):
        return len(self.inner)


def make_pose_group_process(*, contexts, groups, bodies, metadata, slot_arrays, **services):
    """Return process(context, group_token) for rebuild_pose_body_connectivity(process=...).

    The rebuild ignores the return value (native void use), so it is discarded there.
    """
    def process(context, group_token):
        return process_pose_group_bytes(
            context, group_token, contexts=contexts, groups=groups, bodies=bodies,
            metadata=metadata, slot_arrays=slot_arrays, **services)
    return process
