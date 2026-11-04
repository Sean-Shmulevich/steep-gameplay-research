"""Swap-last removal of one constraint link from a body group's link array.

Evidence: native RVA 0x19581c0 (leaf, no unwind entry; ends at 0x141958201),
called by 0x18e28d0 at 0x1418e29b4 as (group, object). The same sequence appears
inlined in engine.pose_body_membership.remove_body_constraints (CENTRAL_IMPULSE.md,
Body removal and attached constraint pruning), whose group layout (+0x40 slot
array, +0x48 count, link +0x80 index, 0xffffffff = detached) is reused here.
Docs: LINK_SOLVER.md, Group link-array removal.
"""
import struct

DETACHED = 0xFFFFFFFF


def remove_pose_group_link(group, link, *, objects, slot_arrays):
    """Remove link from group's link array by moving the last member into its slot.

    group: bytes-like with slot-array pointer at +0x40 and uint32 count at +0x48.
    link: bytes-like with its array index at +0x80.
    slot_arrays: slot-array pointer -> writable bytearray of qword member pointers.
    objects: member pointer -> writable bytes-like link object (for index repair).
    Native sequence: count -= 1; slots[index] = slots[count]; link.index =
    0xffffffff; if index < count, slots[index]'s object gets index. Membership is
    not searched or verified: the stored index is trusted. Index >= old count
    (including the 0xffffffff detached value) or a zero count would make the
    native code read/write outside the array (or through a wrapped count), so
    this reconstruction raises ValueError instead of inventing that behavior.
    """
    index = struct.unpack_from('<I', link, 0x80)[0]
    old = struct.unpack_from('<I', group, 0x48)[0]
    if old == 0 or index >= old:
        raise ValueError('Link index must address an active group slot')
    count = old - 1
    struct.pack_into('<I', group, 0x48, count)
    slots = slot_arrays[struct.unpack_from('<Q', group, 0x40)[0]]
    struct.pack_into('<Q', slots, index * 8, struct.unpack_from('<Q', slots, count * 8)[0])
    struct.pack_into('<I', link, 0x80, DETACHED)
    if index < count:
        moved = objects[struct.unpack_from('<Q', slots, index * 8)[0]]
        struct.pack_into('<I', moved, 0x80, index)
