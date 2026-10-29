"""Recovered completed-group transfer and tracked-body append.

Evidence: LINK_SOLVER.md, Completed-group transfer.
"""
import struct


def _u32(raw, offset):
    return struct.unpack_from('<I', raw, offset)[0]


def _pointer(raw, offset):
    return struct.unpack_from('<Q', raw, offset)[0]


def append_pose_group_bodies(context, group, *, arrays, grow):
    """Append body tokens, with grow(context, descriptor_offset, new_capacity).

    Growth must update descriptor pointer/capacity and preserve its active slots.
    Source count and old tracked count are captured before growth; both array
    pointers are reloaded afterward. Pathological capacity doubling that cannot
    terminate is rejected, rather than reproducing the native infinite loop.
    """
    count = _u32(group, 0x18)
    old = _u32(context, 0x488)
    needed = (count + old) & 0xffffffff
    capacity = _u32(context, 0x48c)
    if needed > capacity:
        if capacity:
            while capacity < needed:
                capacity = (capacity * 2) & 0xffffffff
                if not capacity:
                    raise ValueError('Tracked capacity growth cannot terminate')
        else:
            capacity = needed
        grow(context, 0x480, capacity)
    struct.pack_into('<I', context, 0x488, needed)
    for index in range(count):
        source = arrays[_pointer(group, 0x10)]
        target = arrays[_pointer(context, 0x480)]
        target[(old + index) & 0xffffffff] = source[index]


def transfer_completed_pose_groups(context, *, arrays, groups, grow):
    """Move inactive groups after batch dispatch; retained, well-formed lists.

    arrays maps base tokens to writable slot lists. grow receives context,
    descriptor offset (428 inactive or480 tracked), requested capacity. Unlike
    wake/finalize, this path does not exclude the context's special groups and
    does not reset the group inactive flag or call body reset methods.
    """
    if not context[0x44c]:
        return
    index = (_u32(context, 0x420) - 1) & 0xffffffff
    if index & 0x80000000:
        return
    while index >= 0:
        active = arrays[_pointer(context, 0x418)]
        token = active[index]
        group = groups[token]
        if group[0xa0]:
            slot = _u32(group, 0xc)
            count = (_u32(context, 0x420) - 1) & 0xffffffff
            struct.pack_into('<I', context, 0x420, count)
            active[slot] = active[count]
            if slot < count:
                struct.pack_into('<I', groups[active[slot]], 0xc, slot)
            struct.pack_into('<I', group, 0xc, _u32(context, 0x430))
            capacity = _u32(context, 0x434)
            if _u32(context, 0x430) == capacity:
                grow(context, 0x428, (capacity * 2) & 0xffffffff if capacity else 8)
            target = arrays[_pointer(context, 0x428)]
            target_index = _u32(context, 0x430)
            target[target_index] = token
            struct.pack_into('<I', context, 0x430, (target_index + 1) & 0xffffffff)
            append_pose_group_bodies(context, group, arrays=arrays, grow=grow)
        index -= 1
