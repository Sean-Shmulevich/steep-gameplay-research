"""Deduplicate the groups of selected link objects and process each group once.

Evidence: docs/reconstruction/LINK_SOLVER.md, Body connectivity rebuild
(RVA 0x18e28d0..0x18e2a53). Offsets are evidence anchors, not portable fields.
"""
import struct


def rebuild_pose_body_connectivity(context, output, *, contexts, objects, bodies,
        groups, link, process):
    """Recover the rebuild stage's gates, writes and service order.

    context is the controller context30 token resolved through contexts; output is
    the selected-object token list shared with collect/retire. objects, bodies and
    groups map tokens to mutable bytearrays. link(group, obj) stands for 19581c0
    and process(context, group) for 18e2de0; both are supplied and may mutate any
    mapped bytes. The native local group queue (512 inline slots, doubling through
    18df270, freed at exit when external) is abstracted as a Python list.

    Native assumptions kept as preconditions: the output count is captured once
    while each slot is read when reached, so a callback that shrinks the list
    raises IndexError here where native would read retained stale storage; a null
    group or object is a native fault, here a KeyError. Returns None (native void).
    """
    ctx = contexts[context]
    struct.pack_into('<Q', ctx, 0x464, 0)         # clears 464 and 468
    count = len(output)
    queue = []
    for index in range(count):
        token = output[index]
        obj = objects[token]
        if obj[0x84] & 2:
            continue
        body = bodies[struct.unpack_from('<Q', obj, 8)[0]]
        group_token = struct.unpack_from('<Q', body, 0x10)[0]
        group = groups[group_token]
        if group[0xa0] == 0 and group[0xa1] == 0:
            group[0xa1] = 1
            queue.append(group_token)
        link(group_token, token)                  # for every eligible object
    for group_token in queue:
        groups[group_token][0xa1] = 0
        process(context, group_token)             # return value ignored
        value = struct.unpack_from('<I', ctx, 0x464)[0]
        struct.pack_into('<I', ctx, 0x464, (value + 1) & 0xffffffff)
