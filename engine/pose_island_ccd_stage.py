"""Island stage C4: the stage object at controller+0x40 (begin / dt / finish).

Evidence: docs/reconstruction/LINK_SOLVER.md, "Island swept-contact stage" (this pass).
RVAs: 0x195b190 begin, 0x195af30 kind-6 collection, 0x0ed2ea0 dt store, 0x195c040 finish,
0x195b250 sweep candidate scan (supplied), 0x195a0f0 hit processing (supplied).

Begin collects every constraint whose kind virtual (+0x10) returns 6, first from the
provider's general constraint list (count +0x68, array +0x60), then from every
registered container's children (provider objects count +0x58 / array +0x50, child
array +0x58 / count +0x60). It then removes and destroys every collected constraint
and clears the list. Kind 6 is the one-shot motion-aware point constraint
(pose_constraint_motion); the finish half (static only here) creates new ones from
swept hits, so a kind-6 constraint lives from one substep's C4 finish to the next
substep's C4 begin. "Swept-contact" is our design name (I: continuous collision).

Stage layout: +0x08 controller, +0x10 dt (float32), +0x18 provider (sweep scan input),
+0x20/+0x28/+0x2c hit records (32-byte, ptr/count/capacity), +0x1030/+0x1038/+0x103c
collected kind-6 list (ptr/count/capacity). Memory: PoseFlatMemory-like.
"""
import struct

KIND_SWEPT = 6
LIST = 0x1030
LIST_TAG = 0x11


def _push(mem, stage, constraint, grow):
    count, capacity = mem.d(stage + LIST + 8), mem.d(stage + LIST + 12)
    if count == capacity:
        grow(stage + LIST, (capacity * 2) & 0xFFFFFFFF if capacity else 8)
    count = mem.d(stage + LIST + 8)
    mem.set_q(mem.q(stage + LIST) + 8 * count, constraint)
    mem.set_d(stage + LIST + 8, count + 1)


def reserve_stage_list(mem, descriptor, capacity, *, allocator):
    """0x18d1420 and the inlined copy in 0x195af30: pointer vector reserve, tag 0x11.

    No-op when capacity equals the current one. Existing storage is reallocated (or
    released for capacity 0); null storage is allocated. Count is clamped to capacity.
    """
    if capacity == mem.d(descriptor + 12):
        return
    pointer = mem.q(descriptor)
    if pointer:
        if capacity:
            pointer = allocator.reallocate(pointer, capacity * 8, 0x10, LIST_TAG)
        else:
            allocator.release(pointer)
            pointer = 0
    else:
        pointer = allocator.allocate(capacity * 8, 0x10, LIST_TAG)
    mem.set_q(descriptor, pointer)
    mem.set_d(descriptor + 12, capacity)
    if mem.d(descriptor + 8) > capacity:
        mem.set_d(descriptor + 8, capacity)


def collect_swept_constraints(mem, stage, *, kind, grow):
    """0x195af30. Counts and the provider pointer (stage.controller.provider) are reread
    before every getter and loop test; a container's child count is reread per child."""
    def provider():
        return mem.q(mem.q(stage + 8) + 0x20)
    index = 0
    while index < mem.d(provider() + 0x68):
        constraint = mem.q(mem.q(provider() + 0x60) + 8 * index)
        if kind(constraint) == KIND_SWEPT:
            _push(mem, stage, constraint, grow)
        index += 1
    container_index = 0
    while container_index < mem.d(provider() + 0x58):
        container = mem.q(mem.q(provider() + 0x50) + 8 * container_index)
        child = 0
        while child < mem.d(container + 0x60):
            constraint = mem.q(mem.q(container + 0x58) + 8 * child)
            if kind(constraint) == KIND_SWEPT:
                _push(mem, stage, constraint, grow)
            child += 1
        container_index += 1


def begin_swept_stage(mem, stage, *, kind, grow, remove_cross, remove_local, destroy):
    """0x195b190: collect, then for each collected constraint (count reread per step):
    holders = endpoint metadata(+0x30)+0x20 of +0x08 and +0x10; differing holders call
    remove_cross(stage.controller, c) = 0x18b9210, equal holders remove_local(holder, c)
    = 0x18ba1c0; then the slot is reloaded and a nonnull value receives destroy(c, 1).
    The count is cleared at the end (also when empty)."""
    collect_swept_constraints(mem, stage, kind=kind, grow=grow)
    i = 0
    while i < mem.d(stage + LIST + 8):
        constraint = mem.q(mem.q(stage + LIST) + 8 * i)
        first_holder = mem.q(mem.q(mem.q(constraint + 8) + 0x30) + 0x20)
        second_holder = mem.q(mem.q(mem.q(constraint + 0x10) + 0x30) + 0x20)
        if first_holder != second_holder:
            remove_cross(mem.q(stage + 8), constraint)
        else:
            remove_local(first_holder, constraint)
        constraint = mem.q(mem.q(stage + LIST) + 8 * i)
        if constraint:
            destroy(constraint, 1)
        i += 1
    mem.set_d(stage + LIST + 8, 0)


def store_stage_dt(mem, stage, dt):
    """0x0ed2ea0: stage+0x10 = float32 dt (bit-exact store of the passed float32)."""
    mem.put('<f', stage + 0x10, struct.unpack('<f', struct.pack('<f', dt))[0])


def finish_swept_stage(mem, stage, *, scan, acquire_job_context, run_job, process_hits):
    """0x195c040 order (static, not natively validated): scan = 0x195b250(stage) fills the
    hit records +0x20/+0x28; only if count +0x28 != 0: token = 0x1935890(global
    0x143336900), 0x192bdb0(global, token, 0), then process_hits = 0x195a0f0(stage)."""
    scan(stage)
    if mem.d(stage + 0x28):
        token = acquire_job_context()
        run_job(token)
        process_hits(stage)


def run_swept_stage(mem, controller, dt, *, begin, finish):
    """C4 as called by 0x18b9710: begin, dt store, finish on the stage at controller+0x40,
    reloading controller+0x40 before each call."""
    begin(mem.q(controller + 0x40))
    store_stage_dt(mem, mem.q(controller + 0x40), dt)
    finish(mem.q(controller + 0x40))
