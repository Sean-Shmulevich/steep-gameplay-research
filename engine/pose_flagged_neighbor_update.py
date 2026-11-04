"""Flagged-pair handler for a pair whose key is already in the provider+0x38 tree.

Evidence: docs/reconstruction/LINK_SOLVER.md, "Pair link worker" (router
0x18e0a60) and this module's own section (handler RVA 0x18dfa10, append
0x18dccb0, 4-byte vector reserve 0x18df1e0, basis composition 0x18c16e0).

Recovered local behavior only. The router 0x18e0a60 tail-calls 0x18dfa10 with
(owner, pair, found node index) in rcx/rdx/r8d; the third argument is the node
index in the provider+0x38 tree, not a separate lookup. The node value at +0x10
is the neighbor record this routine updates. Record layout from field use: shape
pair vector entries u32 at +0x48 (low u16 = first-body shape index, high u16 =
second-body shape index), count u32 +0x50, capacity u32 +0x54, state u32 +0x58,
touched byte +0x5c.

Bodies: 3x4 transform at +0x40 (rows +0x40/+0x50/+0x60, translation +0x70),
kind record at +0x30, shape-entry array at +0xb8 (0x48-byte entries), u16 shape
count at +0xc0. Shape entry: shape pointer +0x10, local transform pointer +0x18
(rows +0/+0x10/+0x20, translation +0x30), group masks q+0x28/q+0x30, d+0x38/d+0x3c,
flags byte +0x44. Shape: pointer +0x20 whose +0x48 holds a 16-byte mask pair.

Field names, the flat-memory helper and the services object are authored. The
narrow-phase tester factory (provider+0x68 vtable slot 1), the tester itself
(vtable slot 1) and the global allocator (vtable +8/+0x10/+0x18) are supplied.
Basis composition 0x18c16e0 is pure float32 arithmetic and is reproduced here.
"""
import ctypes
import struct

from engine.pose_pair_link_worker import find_pose_pair_link

ENTRY_STRIDE = 0x48
ENTRY_RESERVE_TAG = 0x2A
ENTRY_RESERVE_ALIGNMENT = 0x10
STATE_DORMANT_ARMED = 1      # authored labels for the observed state values
STATE_CONTACT = 2
STATE_EMPTY = 4


def _f32(x):
    # C double->float cast: round to nearest, overflow to infinity.
    return ctypes.c_float(x).value


def _mul(a, b):
    return _f32(a * b)


def _add(a, b):
    return _f32(a + b)


def _dot3(x, y, z, cx, cy, cz):
    # ((x*cx + y*cy) + z*cz), each operation rounded to float32 (movss/mulss/addss).
    return _add(_add(_mul(x, cx), _mul(y, cy)), _mul(z, cz))


def read_pose_transform(mem, address):
    """12 floats: three rows of 3 at +0/+0x10/+0x20 and translation at +0x30."""
    out = []
    for row in range(4):
        for col in range(3):
            out.append(mem.get('<f', address + row * 0x10 + col * 4))
    return out


def compose_pose_shape_transform(local, parent):
    """0x18c16e0 basis product plus the caller's inline translation (float32)."""
    out = []
    for i in range(3):
        lx, ly, lz = local[3 * i:3 * i + 3]
        for j in range(3):
            out.append(_dot3(lx, ly, lz, parent[j], parent[3 + j], parent[6 + j]))
    lx, ly, lz = local[9:12]
    for j in range(3):
        out.append(_add(_dot3(lx, ly, lz, parent[j], parent[3 + j], parent[6 + j]), parent[9 + j]))
    return out


def reserve_pose_entry_vector(mem, vector, capacity, *, allocator):
    """0x18df1e0: 4-byte element reserve (tag 0x2a); 0x18def10's shape otherwise."""
    capacity &= 0xFFFFFFFF
    if capacity == mem.d(vector + 0xC):
        return
    pointer = mem.q(vector)
    size = (capacity * 4) & 0xFFFFFFFF
    if pointer:
        if capacity:
            pointer = allocator.reallocate(pointer, size, ENTRY_RESERVE_ALIGNMENT, ENTRY_RESERVE_TAG)
        else:
            allocator.release(pointer)
            pointer = 0
    else:
        pointer = allocator.allocate(size, ENTRY_RESERVE_ALIGNMENT, ENTRY_RESERVE_TAG)
    mem.set_q(vector, pointer)
    mem.set_d(vector + 0xC, capacity)
    if mem.d(vector + 8) > capacity:
        mem.set_d(vector + 8, capacity)


def append_pose_shape_pair(mem, record, first_index, second_index, *, allocator):
    """0x18dccb0: push (first u16 | second u16 << 16) onto record+0x48; returns new index."""
    capacity = mem.d(record + 0x54)
    if mem.d(record + 0x50) == capacity:
        reserve_pose_entry_vector(mem, record + 0x48, (capacity * 2) & 0xFFFFFFFF if capacity else 8,
                                  allocator=allocator)
    used = mem.d(record + 0x50)
    mem.set_d(mem.q(record + 0x48) + used * 4, (first_index & 0xFFFF) | (second_index & 0xFFFF) << 16)
    mem.set_d(record + 0x50, used + 1)
    return used


def _find_shape_pair(mem, record, first_index, second_index, count):
    entries = mem.q(record + 0x48)
    for k in range(count & 0xFFFF):
        if mem.w(entries + 4 * k) == first_index and mem.w(entries + 4 * k + 2) == second_index:
            return k
    return -1


def _swap_remove(mem, record, k):
    count = (mem.d(record + 0x50) - 1) & 0xFFFFFFFF
    mem.set_d(record + 0x50, count)
    entries = mem.q(record + 0x48)
    mem.set_d(entries + 4 * k, mem.d(entries + 4 * count))


def _active(mem, owner, body):
    kind = mem.q(body + 0x30)
    if mem.w(kind + 0x50) & 0x8000:
        return mem.b(kind + 0x53) & 0xF != 2
    return mem.d(kind + 0x1C) == mem.d(mem.q(owner) + 0x180)


def _solid(flags):
    return ((flags >> 1) & flags) & 4 != 0


def update_pose_flagged_neighbor(mem, owner, pair, index, services):
    """0x18dfa10(owner, pair, index): refresh a neighbor record's shape-pair list.

    services.select_tester(factory, shape_a, shape_b) -> tester pointer
    (factory = provider+0x68, native factory vtable[1]); services.test_overlap(
    tester, world_a, world_b, shape_a, shape_b) -> bool (native tester vtable[1],
    low byte of rax); services.allocator for 0x18df1e0.
    """
    first, second = mem.q(pair), mem.q(pair + 8)
    count_a, count_b = mem.w(first + 0xC0), mem.w(second + 0xC0)
    group_a = mem.q(mem.q(first + 0x30) + 0x20)
    group_b = mem.q(mem.q(second + 0x30) + 0x20)
    body_a = read_pose_transform(mem, first + 0x40)
    body_b = read_pose_transform(mem, second + 0x40)
    dormant = not _active(mem, owner, first) and not _active(mem, owner, second)
    record = mem.q(mem.q(mem.q(owner) + 0x38) + index * 32 + 0x10)
    mem.set_b(record + 0x5C, 1)
    if dormant:
        if mem.d(record + 0x58) == STATE_DORMANT_ARMED:
            mem.set_d(record + 0x58, STATE_CONTACT)
        return
    for i in range(count_a):
        entry_a = mem.q(first + 0xB8) + i * ENTRY_STRIDE
        shape_a = mem.q(entry_a + 0x10)
        if not shape_a:
            continue
        world_a = compose_pose_shape_transform(read_pose_transform(mem, mem.q(entry_a + 0x18)), body_a)
        entry_a = mem.q(first + 0xB8) + i * ENTRY_STRIDE      # r12 reload after the composition
        if not _solid(mem.b(entry_a + 0x44)):
            for j in range(count_b):
                k = _find_shape_pair(mem, record, i, j, mem.d(record + 0x50))
                if k != -1:
                    _swap_remove(mem, record, k)
            continue
        mask_a = mem.q(shape_a + 0x20) + 0x48
        for j in range(count_b):
            count = mem.d(record + 0x50)
            entry_b = mem.q(second + 0xB8) + j * ENTRY_STRIDE
            shape_b = mem.q(entry_b + 0x10)
            k = _find_shape_pair(mem, record, i, j, count)
            if not shape_b:
                continue                                    # stale entry kept
            mask_b = mem.q(shape_b + 0x20) + 0x48
            hit = False
            if _solid(mem.b(entry_b + 0x44)) and _groups_overlap(mem, first, entry_a, entry_b,
                                                                  group_a == group_b):
                if (mem.q(mask_a + 8) & mem.q(mask_b)) | (mem.q(mask_b + 8) & mem.q(mask_a)):
                    world_b = compose_pose_shape_transform(read_pose_transform(mem, mem.q(entry_b + 0x18)), body_b)
                    factory = mem.q(mem.q(owner) + 0x68)
                    tester = services.select_tester(factory, shape_a, shape_b)
                    hit = bool(services.test_overlap(tester, world_a, world_b, shape_a, shape_b))
            if hit:
                if k == -1:
                    append_pose_shape_pair(mem, record, i, j, allocator=services.allocator)
                mem.set_d(record + 0x58, STATE_CONTACT)
            elif k != -1:
                _swap_remove(mem, record, k)
    if mem.d(record + 0x50) == 0:
        mem.set_d(record + 0x58, STATE_EMPTY)


def _groups_overlap(mem, first, entry_a, entry_b, same_group):
    q_test = ((mem.q(entry_b + 0x30) & mem.q(entry_a + 0x28)) |
              (mem.q(entry_a + 0x30) & mem.q(entry_b + 0x28))) != 0
    if not same_group:
        return q_test
    d_test = ((mem.d(entry_b + 0x38) & mem.d(entry_a + 0x3C)) |
              (mem.d(entry_b + 0x3C) & mem.d(entry_a + 0x38))) != 0
    if mem.b(mem.q(first + 0x30) + 0x52) & 0x10:
        return d_test
    return q_test and d_test


def route_pose_flagged_pair_indexed(mem, owner, pair, services):
    """0x18e0a60 with the found index forwarded in r8d to 0x18dfa10.

    The worker module's route_pose_flagged_pair calls update_neighbor(owner,
    pair) and drops the index; this variant keeps the native third argument.
    """
    index, _ = find_pose_pair_link(mem, mem.q(owner) + 0x38, mem.q(pair + 0x10))
    if index == -1:
        services.create_neighbor(owner, pair)      # 0x18e01e0
    else:
        update_pose_flagged_neighbor(mem, owner, pair, index, services)
