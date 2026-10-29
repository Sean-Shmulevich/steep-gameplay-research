"""Recovered group ordering and batch formation.

Evidence: LINK_SOLVER.md, Group batch formation. Retained serial storage only.
"""
import struct


def _u32(raw, offset):
    return struct.unpack_from('<I', raw, offset)[0]


def _pointer(raw, offset):
    return struct.unpack_from('<Q', raw, offset)[0]


def _signed(value):
    value &= 0xffffffff
    return value - 0x100000000 if value & 0x80000000 else value


def pose_group_work(group):
    return (_u32(group, 0x98) + _u32(group, 0x48)) & 0xffffffff


def compare_pose_group_work(first, second):
    """Native descending comparator, including signed subtraction overflow."""
    return _signed(pose_group_work(second) - pose_group_work(first))


def order_pose_groups(context, *, arrays, groups, sort_prefix):
    """Partition in place; sort_prefix(slots, count, comparator) supplies CRT sort.

    Equal-key ordering and overflow-sensitive sorting are not silently replaced
    with Python's stable sort. The service must mutate only the requested prefix.
    """
    count = _u32(context, 0x420)
    if not count:
        return
    slots = arrays[_pointer(context, 0x418)]
    end = count
    index = 0
    while index < end:
        if pose_group_work(groups[slots[index]]) == 0:
            end -= 1
            if index == end:
                break
            slots[index], slots[end] = slots[end], slots[index]
        else:
            index += 1
    if end > 1:
        sort_prefix(slots, end, lambda a, b: compare_pose_group_work(groups[a], groups[b]))
    # Count and array are reloaded after the sorting service.
    for index in range(_u32(context, 0x420)):
        token = arrays[_pointer(context, 0x418)][index]
        struct.pack_into('<I', groups[token], 0xc, index)


def run_pose_group_batches(context, *, context_token, scalar, settings_token,
                           worker_capacity, arrays, groups, batches, sort_prefix,
                           grow, dispatch, finish):
    """Prepare batches, dispatch workers, clear the active batch count, finish.

    batches maps record addresses to writable 16-byte records. arrays maps the
    active span base to its retained slots. grow(context, capacity) must update
    pointer438/capacity444 and batches, preserving existing records. dispatch gets
    (worker_count, context_token+0x308), with jobs already updated inside context.
    Job owner pointers must already be initialized by the caller. finish(context)
    supplies completed-group transfer. No default threading or allocator policy.
    """
    count = _u32(context, 0x420)
    order_pose_groups(context, arrays=arrays, groups=groups, sort_prefix=sort_prefix)
    struct.pack_into('<I', context, 0x440, 0)
    index = 0
    while index < count:
        capacity = _u32(context, 0x444)
        if _u32(context, 0x440) == capacity:
            new_capacity = (capacity * 2) & 0xffffffff if capacity else 8
            if new_capacity != capacity:
                grow(context, new_capacity)
                struct.pack_into('<I', context, 0x444, new_capacity)
                if _u32(context, 0x440) > new_capacity:
                    struct.pack_into('<I', context, 0x440, new_capacity)
        batch_index = _u32(context, 0x440)
        batch = batches[_pointer(context, 0x438) + 16 * batch_index]
        struct.pack_into('<I', context, 0x440, (batch_index + 1) & 0xffffffff)
        struct.pack_into('<I', batch, 0, 0)
        struct.pack_into('<Q', batch, 8, _pointer(context, 0x418) + index * 8)
        work = 0
        while index < count:
            token = arrays[_pointer(context, 0x418)][index]
            weight = max(1, pose_group_work(groups[token]))
            struct.pack_into('<I', batch, 0, (_u32(batch, 0) + 1) & 0xffffffff)
            work = (work + weight) & 0xffffffff
            index += 1
            if _signed(work) >= 25:
                break
    workers = min(worker_capacity, _u32(context, 0x440), 32)
    if type(worker_capacity) is not int or not 0 <= worker_capacity <= 0xffffffff:
        raise ValueError('Unsigned dispatcher worker capacity required')
    for index in range(workers):
        struct.pack_into('<fQ', context, 0x14 + 0x18 * index, scalar, settings_token)
    struct.pack_into('<I', context, 0x448, 0)
    if workers:
        dispatch(workers, context_token + 0x308)
    struct.pack_into('<I', context, 0x440, 0)
    finish(context)
