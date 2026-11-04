"""Flagged-pair neighbor creation: per-shape overlap sweep that builds one neighbor record.

Evidence: docs/reconstruction/LINK_SOLVER.md, "Pair link worker" (the flagged route
0x18e0a60 tail-calls 0x18e01e0 when the pair key is absent from the provider+0x38
tree) and "Flagged neighbor create" (this routine, 0x18e01e0..0x18e0893), with its
leaf callees:

- 0x18c16e0 basis composition (same float32 order as LINK_SOLVER.md's transform
  helper section; the translation is computed inline by 0x18e01e0),
- 0x18de2e0 neighbor record acquire (pops owner+0x48, else allocates 0x60 bytes),
- 0x195c3e0 copy of the pair triple into record+8/+0x10/+0x18,
- 0x18dccb0 shape-pair push (u16 i | u16 j << 16) onto record+0x48,
- 0x18df150 / 0x18df1e0 vector reserves (tags 0x27 / 0x2a; 8- and 4-byte elements).

Recovered local behavior only. Field names, the flat-memory helper, the query tuple
and the services object are authored design choices. The two virtual calls are
supplied services: the collider selector (provider+0x68 object, vtable slot 1, with
the two shape pointers) and the overlap test (selected object, vtable slot 1, with
a pointer to the 0x90-byte query frame). The allocator and the global serial
counter are supplied as in engine.pose_pair_link_worker.

Float arithmetic is rounded to float32 after every multiply and add, in native
operand order. Non-finite fixture values are outside the validated domain.
"""
import math
import struct

SHAPE_ENTRY_BYTES = 72
NEIGHBOR_RECORD_BYTES = 0x60
NEIGHBOR_RECORD_ALIGNMENT = 0x10
NEIGHBOR_RECORD_TAG = 0x29
NEIGHBOR_VECTOR_TAG = 0x27          # 0x18df150, owner+0x18 pointer vector
SHAPE_PAIR_VECTOR_TAG = 0x2A        # 0x18df1e0, record+0x48 u32 vector
VECTOR_ALIGNMENT = 0x10
NEW_NEIGHBOR_STATE = 1
SAME_GROUP_MASK_ONLY = 0x10         # kind+0x52 bit for the same-group branch
# Image addresses written by the 0x18de2e0 constructor (evidence anchors only).
NEIGHBOR_BASE_VTABLE = 0x1429c9fd0
NEIGHBOR_VTABLE = 0x1429ca778


def _f32(x):
    try:
        return struct.unpack('<f', struct.pack('<f', x))[0]
    except OverflowError:
        return math.copysign(math.inf, x)


def _read_frame(mem, address):
    """Three basis rows at +0,+0x10,+0x20 and a translation at +0x30 (fourth lanes ignored)."""
    rows = tuple(tuple(mem.get('<f', address + r * 0x10 + c * 4) for c in range(3)) for r in range(4))
    return rows[:3], rows[3]


def compose_pose_shape_frame(parent, local):
    """0x18c16e0 basis plus the inline translation of 0x18e01e0; float32 each step.

    basis[i][j] = ((L[i].x*P[0][j] + L[i].y*P[1][j]) + L[i].z*P[2][j])
    translation[j] = (((l.x*P[0][j] + l.y*P[1][j]) + l.z*P[2][j]) + p[j])
    """
    (P, p), (L, l) = parent, local

    def row(v):
        return tuple(_f32(_f32(_f32(_f32(v[0] * P[0][j]) + _f32(v[1] * P[1][j])) + _f32(v[2] * P[2][j])))
                     for j in range(3))
    basis = tuple(row(L[i]) for i in range(3))
    translation = tuple(_f32(t + p[j]) for j, t in enumerate(row(l)))
    return basis, translation


def reserve_pose_tagged_vector(mem, vector, capacity, *, allocator, element_size, tag):
    """0x18df150 (8-byte, tag 0x27) / 0x18df1e0 (4-byte, tag 0x2a); 0x18def10's shape.

    vector: pointer q@0, count u32@8, capacity u32@0xC. Equal capacity is a no-op;
    null pointer -> allocate(size, 0x10, tag); nonnull -> reallocate for nonzero
    capacity or release and null for zero. Size is the u32 truncation of
    capacity*element_size. Capacity is stored and a larger count clamped.
    """
    capacity &= 0xFFFFFFFF
    if capacity == mem.d(vector + 0xC):
        return
    pointer = mem.q(vector)
    size = (capacity * element_size) & 0xFFFFFFFF
    if pointer:
        if capacity:
            pointer = allocator.reallocate(pointer, size, VECTOR_ALIGNMENT, tag)
        else:
            allocator.release(pointer)
            pointer = 0
    else:
        pointer = allocator.allocate(size, VECTOR_ALIGNMENT, tag)
    mem.set_q(vector, pointer)
    mem.set_d(vector + 0xC, capacity)
    if mem.d(vector + 8) > capacity:
        mem.set_d(vector + 8, capacity)


def acquire_pose_neighbor_record(mem, pools, *, allocator, next_serial,
                                 vtables=(NEIGHBOR_BASE_VTABLE, NEIGHBOR_VTABLE)):
    """0x18de2e0(owner+0x28): pop owner+0x48's free list, else allocate and construct.

    pools is owner+0x28 as native passes it; the free list is pools+0x20 (pointer)
    with count u32 at pools+0x28. A popped record is returned as is: no destructor
    and no reinitialization (0x195c360 cleared it at retire). Otherwise 0x60 bytes
    come from allocate(0x60, 0x10, 0x29) and are constructed in place; a null
    allocation is returned as 0 (the caller then faults natively).
    """
    used = mem.d(pools + 0x28)
    if used:
        used -= 1
        mem.set_d(pools + 0x28, used)
        return mem.q(mem.q(pools + 0x20) + used * 8)
    record = allocator.allocate(NEIGHBOR_RECORD_BYTES, NEIGHBOR_RECORD_ALIGNMENT, NEIGHBOR_RECORD_TAG)
    if not record:
        return 0
    for offset in (8, 0x10, 0x18):
        mem.set_q(record + offset, 0)
    mem.set_q(record, vtables[0])
    for offset in (0x20, 0x28, 0x30, 0x38):
        mem.set_q(record + offset, 0)
    mem.set_d(record + 0x40, next_serial())
    mem.set_q(record, vtables[1])
    mem.set_q(record + 0x48, 0)
    mem.set_q(record + 0x50, 0)              # shape-pair count and capacity
    mem.set_d(record + 0x58, 0xFFFFFFFF)
    mem.set_b(record + 0x5C, 0)
    return record


def push_pose_shape_pair(mem, record, first_index, second_index, *, allocator):
    """0x18dccb0: append u32 (first u16 | second u16 << 16) to record+0x48; returns its index."""
    vector = record + 0x48
    used, capacity = mem.d(vector + 8), mem.d(vector + 0xC)
    if used == capacity:
        reserve_pose_tagged_vector(mem, vector, (capacity * 2) & 0xFFFFFFFF if capacity else 8,
                                   allocator=allocator, element_size=4, tag=SHAPE_PAIR_VECTOR_TAG)
    used = mem.d(vector + 8)
    mem.set_d(mem.q(vector) + used * 4, (first_index & 0xFFFF) | (second_index & 0xFFFF) << 16)
    mem.set_d(vector + 8, used + 1)
    return used


def _enabled(flags):
    return (flags >> 1) & flags & 4          # bits 2 and 3 both set


def _masks_overlap(mem, entry_a, entry_b, same_group, first):
    def wide():
        return (mem.q(entry_b + 0x30) & mem.q(entry_a + 0x28)) | (mem.q(entry_a + 0x30) & mem.q(entry_b + 0x28))

    def narrow():
        return (mem.d(entry_b + 0x38) & mem.d(entry_a + 0x3C)) | (mem.d(entry_b + 0x3C) & mem.d(entry_a + 0x38))
    if not same_group:
        return bool(wide())
    if mem.b(mem.q(first + 0x30) + 0x52) & SAME_GROUP_MASK_ONLY:   # kind reread per pair
        return bool(narrow())
    return bool(wide()) and bool(narrow())


def create_pose_flagged_neighbor(mem, owner, pair, services):
    """0x18e01e0(owner, pair): test every enabled shape pair; collect overlaps in one record.

    Captured at entry: both bodies, both shape counts (u16 @0xc0), both kind+0x20
    group words and both 3x4 body frames (+0x40..+0x7c). Reread: each body's shape
    array (+0xb8; A per outer step, B per inner step), shape-entry masks, A's kind
    +0x52, provider+0x68 and the pair triple at record creation. shapeA+0x20 and
    shape A's world frame are fixed per outer step.

    For overlap (i, j) the first hit acquires a record (0x18de2e0), copies the pair
    (0x195c3e0) and sets byte +0x5c = 1 then state u32 +0x58 = 1; every hit pushes
    (i, j). A record, if any, is pushed once onto owner+0x18 (reserve 2*cap or 8,
    tag 0x27). Returns the record pointer or 0 (authored; native returns nothing).
    services: select_collider(dispatcher, shape_a, shape_b) -> object,
    test_overlap(object, query) -> bool with query = (frame_a, frame_b, shape_a,
    shape_b), frame = (basis rows, translation); allocator; next_serial().
    """
    first, second = mem.q(pair), mem.q(pair + 8)
    count_a = mem.w(first + 0xC0)
    group_a = mem.q(mem.q(first + 0x30) + 0x20)
    group_b = mem.q(mem.q(second + 0x30) + 0x20)
    frame_a = _read_frame(mem, first + 0x40)
    count_b = mem.w(second + 0xC0)
    frame_b = _read_frame(mem, second + 0x40)
    record = 0
    for i in range(count_a):
        entry_a = mem.q(first + 0xB8) + i * SHAPE_ENTRY_BYTES
        shape_a = mem.q(entry_a + 0x10)
        if not shape_a or not _enabled(mem.b(entry_a + 0x44)):
            continue
        world_a = compose_pose_shape_frame(frame_a, _read_frame(mem, mem.q(entry_a + 0x18)))
        filter_a = mem.q(shape_a + 0x20)
        for j in range(count_b):
            entry_b = mem.q(second + 0xB8) + j * SHAPE_ENTRY_BYTES
            shape_b = mem.q(entry_b + 0x10)
            if not shape_b or not _enabled(mem.b(entry_b + 0x44)):
                continue
            filter_b = mem.q(shape_b + 0x20)
            if not _masks_overlap(mem, entry_a, entry_b, group_a == group_b, first):
                continue
            if not ((mem.q(filter_a + 0x50) & mem.q(filter_b + 0x48)) |
                    (mem.q(filter_b + 0x50) & mem.q(filter_a + 0x48))):
                continue
            world_b = compose_pose_shape_frame(frame_b, _read_frame(mem, mem.q(entry_b + 0x18)))
            collider = services.select_collider(mem.q(mem.q(owner) + 0x68), shape_a, shape_b)
            if not services.test_overlap(collider, (world_a, world_b, shape_a, shape_b)):
                continue
            if not record:
                record = acquire_pose_neighbor_record(mem, owner + 0x28, allocator=services.allocator,
                                                      next_serial=services.next_serial)
                if not record:
                    raise MemoryError('neighbor record allocation returned null (native faults)')
                for offset in (0, 8, 0x10):
                    mem.set_q(record + 8 + offset, mem.q(pair + offset))
                mem.set_b(record + 0x5C, 1)
                mem.set_d(record + 0x58, NEW_NEIGHBOR_STATE)
            push_pose_shape_pair(mem, record, i, j, allocator=services.allocator)
    if record:
        vector = owner + 0x18
        used, capacity = mem.d(vector + 8), mem.d(vector + 0xC)
        if used == capacity:
            reserve_pose_tagged_vector(mem, vector, (capacity * 2) & 0xFFFFFFFF if capacity else 8,
                                       allocator=services.allocator, element_size=8, tag=NEIGHBOR_VECTOR_TAG)
        used = mem.d(vector + 8)
        mem.set_q(mem.q(vector) + used * 8, record)
        mem.set_d(vector + 8, used + 1)
    return record
