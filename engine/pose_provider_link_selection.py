"""Destructive provider-tree selection for body connectivity refresh.

Evidence: docs/reconstruction/LINK_SOLVER.md, Provider link-tree selection.
"""
import struct

from engine.pose_body_tree import _Tree


def select_pose_provider_links(provider, rows, *, bodies, metadata, node_arrays):
    """Return selected value pointers, removing each matched node from the tree.

    provider is the provider object; its indexed red-black tree descriptor starts
    at+8 (node pointer, active count, free count, root index, free-list head).
    rows are 24-byte link snapshots. A row is eligible when its first endpoint's
    metadata has priority50 bit15 set and state53 low nibble != 2. Its third qword
    is an unsigned64 key. Output storage growth is abstracted as a Python list.
    """
    descriptor = memoryview(provider)[8:]
    selected = []
    for row in rows:
        endpoint = struct.unpack_from('<Q', row, 0)[0]
        meta = metadata[struct.unpack_from('<Q', bodies[endpoint], 0x30)[0]]
        if not struct.unpack_from('<H', meta, 0x50)[0] & 0x8000:
            continue
        if meta[0x53] & 0xF == 2:
            continue
        key = struct.unpack_from('<Q', row, 0x10)[0]
        index = struct.unpack_from('<i', descriptor, 0x14)[0]
        if index == -1:
            continue
        nodes = node_arrays[struct.unpack_from('<Q', descriptor, 0)[0]]
        tree = _Tree(descriptor, nodes)
        while index != -1:
            node_key = struct.unpack_from('<Q', nodes, index * 32 + 0x18)[0]
            if key == node_key:
                selected.append(struct.unpack_from('<Q', nodes, index * 32 + 0x10)[0])
                tree.remove(index, key_size=8)
                break
            index = tree.link(index, 0 if key < node_key else 4)
    return selected
