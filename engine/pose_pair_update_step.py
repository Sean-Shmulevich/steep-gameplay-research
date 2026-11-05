"""Broadphase-driven pair update step: removed pairs -> select/rebuild, new pairs -> jobs.

Evidence: docs/reconstruction/LINK_SOLVER.md, "Pair update step" (RVA
0x18b8fa0..0x18b90b2, sole direct caller the thunk 0x18ae2b0; helpers 0x19598b0
and 0x18df490). Offsets are evidence anchors, not portable API fields.

Recovered local behavior only. The controller is the 0x78-byte object built by
0x18b8150 (controller+0x28 broadphase, +0x30 island context, +0x38 narrow-phase
provider, +0x48 phase word, +0x4c frame counter). The routine:

  1. controller+0x48 = 1
  2. 0x19598b0(controller+0x28): broadphase virtual +0x90 (update), returns 1
  3. removed pairs: count = vcall +0x60, pairs = vcall +0x68 (count first)
     0x18dedf0(controller+0x38, pairs, count, &output)       -> select
     0x18e28d0(controller+0x30, &output)                      -> rebuild
  4. new pairs: count = vcall +0x40, pairs = vcall +0x48 (count first)
     0x18ddc40(controller+0x38, pairs, count, &output)       -> jobs
     (the SAME output vector: the jobs' retire stage consumes the selection)
  5. free output storage through the global allocator (+0x18) when its capacity is
     nonzero and its pointer is not the 0x200-slot inline buffer
  6. broadphase virtual +0x88 (no-op `ret` in the observed class)
  7. controller+0x4c += 1; broadphase u32 +8 = controller+0x4c;
     0x18df490(controller+0x38, controller+0x4c): provider u32 +0x180 = frame
  8. controller+0x48 = 2; return 1

Each controller field is reloaded at every use, so service mutations of the
controller are observed by later steps (the context +0x30 is read once, at its
single use). Pair arrays are 24-byte rows (body, body, unsigned64 key): the same
row format the body-event refresh builds, confirmed by the 0x18 stride in
0x18dedf0 and by the pair worker's index*24 reads.

The broadphase is reached through vcall(token, slot) so a harness can supply any
virtual table; pose_dynamic_tree_broadphase_vcall recovers the accessors of the
observed class (vtable image address 0x1429ca8a0, "Dynamic tree multi-threaded
broad phase"), whose update (0x199c880) stays supplied.
"""
import struct

INLINE_CAPACITY = 0x200
INLINE = 'inline'           # authored marker for the native stack buffer
PHASE_RUNNING = 1
PHASE_DONE = 2

UPDATE_SLOT = 0x90          # via 0x19598b0
REMOVED_COUNT_SLOT = 0x60
REMOVED_PAIRS_SLOT = 0x68
NEW_COUNT_SLOT = 0x40
NEW_PAIRS_SLOT = 0x48
FINISH_SLOT = 0x88

DYNAMIC_TREE_BROADPHASE_VTABLE = 0x1429ca8a0   # evidence anchor only


class PosePairOutputVector:
    """Authored stand-in for the native {ptr, u32 count, u32 capacity} descriptor
    whose storage starts as a 0x200-entry inline stack buffer. Services that grow
    it set storage to an external token and capacity to the new capacity."""

    def __init__(self):
        self.items = []
        self.capacity = INLINE_CAPACITY
        self.storage = INLINE


def _q(raw, offset):
    return struct.unpack_from('<Q', raw, offset)[0]


def _d(raw, offset):
    return struct.unpack_from('<I', raw, offset)[0]


def pose_dynamic_tree_broadphase_vcall(objects, update, finish=None):
    """Recovered accessors of the observed broadphase class.

    +0x40 0x1940410: u32 [[obj+0xf8]+8]   new-pair count
    +0x48 0x1940400: q   [[obj+0xf8]]     new-pair array
    +0x60 0x19403f0: u32 [obj+0x120]      removed-pair count
    +0x68 0x19403e0: q   [obj+0x118]      removed-pair array
    +0x88 0x075e600: ret (no effect); finish(token) is an optional observer
    +0x90 0x199c880: update(token), supplied (swaps +0xf8/+0x100 and rebuilds)
    objects maps tokens to bytearrays; the +0xf8 target must be mapped too.
    """
    def vcall(token, slot):
        obj = objects[token]
        if slot == NEW_COUNT_SLOT:
            return _d(objects[_q(obj, 0xf8)], 8)
        if slot == NEW_PAIRS_SLOT:
            return _q(objects[_q(obj, 0xf8)], 0)
        if slot == REMOVED_COUNT_SLOT:
            return _d(obj, 0x120)
        if slot == REMOVED_PAIRS_SLOT:
            return _q(obj, 0x118)
        if slot == FINISH_SLOT:
            if finish is not None:
                finish(token)
            return None
        if slot == UPDATE_SLOT:
            update(token)
            return None
        raise KeyError(slot)
    return vcall


def run_pose_pair_update_step(controller, *, objects, vcall, select, rebuild, jobs,
                              release):
    """0x18b8fa0(controller) -> True.

    controller is a writable bytearray; objects maps broadphase and provider tokens
    to bytearrays (only broadphase u32 +8 and provider u32 +0x180 are written
    here). Services, in native order:
      vcall(broadphase, 0x90 / 0x60 / 0x68 / 0x40 / 0x48 / 0x88) -> int or None
      select(provider, pairs, count, output)    0x18dedf0 (resets output count)
      rebuild(context, output)                  0x18e28d0
      jobs(provider, pairs, count, output)      0x18ddc40
      release(storage)                          allocator vtable +0x18
    output is one PosePairOutputVector shared by all three stages.
    """
    struct.pack_into('<I', controller, 0x48, PHASE_RUNNING)
    vcall(_q(controller, 0x28), UPDATE_SLOT)            # 0x19598b0, result ignored
    output = PosePairOutputVector()
    broadphase = _q(controller, 0x28)
    count = vcall(broadphase, REMOVED_COUNT_SLOT) & 0xFFFFFFFF
    pairs = vcall(broadphase, REMOVED_PAIRS_SLOT) & 0xFFFFFFFFFFFFFFFF
    select(_q(controller, 0x38), pairs, count, output)
    rebuild(_q(controller, 0x30), output)
    broadphase = _q(controller, 0x28)
    count = vcall(broadphase, NEW_COUNT_SLOT) & 0xFFFFFFFF
    pairs = vcall(broadphase, NEW_PAIRS_SLOT) & 0xFFFFFFFFFFFFFFFF
    jobs(_q(controller, 0x38), pairs, count, output)
    if output.capacity & 0xFFFFFFFF and output.storage != INLINE:
        release(output.storage)
    vcall(_q(controller, 0x28), FINISH_SLOT)
    struct.pack_into('<I', controller, 0x4c, (_d(controller, 0x4c) + 1) & 0xFFFFFFFF)
    struct.pack_into('<I', objects[_q(controller, 0x28)], 8, _d(controller, 0x4c))
    struct.pack_into('<I', objects[_q(controller, 0x38)], 0x180, _d(controller, 0x4c))
    struct.pack_into('<I', controller, 0x48, PHASE_DONE)
    return True
