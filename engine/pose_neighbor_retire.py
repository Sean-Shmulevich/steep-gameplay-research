"""Neighbor-record retire stage: in-order tree sweep that queues state-4 records.

Evidence: docs/reconstruction/LINK_SOLVER.md, "Neighbor record retire" (RVA
0x18de510) and its endpoint clear 0x195c360.

Recovered local behavior only. The provider's second indexed tree (descriptor at
+0x38, 64-bit keys) holds records whose dword +0x58 is a state. Each record in
state 4 is removed from the tree (0x19a40b0, reconstructed by
engine.pose_body_tree._Tree.remove(key_size=8)), leaves its selector0 endpoint
rings (0x195c270, engine.pose_endpoint_rings), has its endpoints cleared
(0x195c360) and is appended to the vector at +0x48 of a slot owner chosen
round-robin, like the link retire stage 0x18de440 uses +0x28.
"""
import struct

from engine.pose_body_tree import _Tree

NEIGHBOR_RETIRE_STATE = 4


def clear_pose_neighbor_record(record):
    """0x195c360: count u32@0x50 decremented to zero if positive; zero +0x10 then +8."""
    struct.pack_into('<I', record, 0x50, 0)
    struct.pack_into('<Q', record, 0x10, 0)
    struct.pack_into('<Q', record, 8, 0)


def _successor(tree, index):
    right = tree.link(index, 4)
    if right != -1:
        while tree.link(right, 0) != -1:
            right = tree.link(right, 0)
        return right
    current, parent = index, tree.link(index, 8)
    while parent != -1 and tree.link(parent, 0) != current:
        current, parent = parent, tree.link(parent, 8)
    return parent


def retire_pose_neighbor_records(provider, divisor, *, node_arrays, records, queue_owners,
                                 queue_arrays, detach, clear=None, reserve, remove=None):
    """Sweep provider+0x38's tree in key order, retiring state-4 values.

    Per node: read value (+0x10), compute the in-order successor from the
    current links, then if value.state58 == 4: remove(tree, index), detach(value, 0),
    read owner = provider qword 0x70 + 8*slot, clear(value), push value onto
    owner+0x48 (reserve to 2*capacity or 8 when full), slot = (slot+1) % divisor.
    Unsigned 32-bit divide; divisor 0 raises ZeroDivisionError after the first
    queued record, where native faults. The successor is captured before removal.
    """
    divisor &= 0xFFFFFFFF
    clear = clear or (lambda token: clear_pose_neighbor_record(records[token]))
    descriptor = memoryview(provider)[0x38:]
    remove = remove or (lambda tree, index: tree.remove(index, key_size=8))

    def tree():
        return _Tree(descriptor, node_arrays[struct.unpack_from('<Q', descriptor, 0)[0]])

    index = struct.unpack_from('<i', descriptor, 0x14)[0]
    if index == -1:
        return
    while tree().link(index, 0) != -1:
        index = tree().link(index, 0)
    slot = 0
    while index != -1:
        current = tree()
        value = struct.unpack_from('<Q', current.n, index * 32 + 0x10)[0]
        following = _successor(current, index)
        if struct.unpack_from('<I', records[value], 0x58)[0] == NEIGHBOR_RETIRE_STATE:
            remove(current, index)
            detach(value, 0)
            owner = queue_owners[struct.unpack_from('<Q', provider, 0x70 + 8 * slot)[0]]
            clear(value)
            vector = memoryview(owner)[0x48:0x58]
            used, capacity = struct.unpack_from('<II', vector, 8)
            if used == capacity:
                reserve(vector, (capacity * 2) & 0xFFFFFFFF if capacity else 8)
            pointer, used = struct.unpack_from('<QI', vector, 0)
            elements = queue_arrays[pointer]
            if len(elements) < used * 8 + 8:
                raise IndexError('queue vector storage is smaller than its count')
            struct.pack_into('<Q', elements, used * 8, value)
            struct.pack_into('<I', vector, 8, (used + 1) & 0xFFFFFFFF)
            slot = ((slot + 1) & 0xFFFFFFFF) % divisor
        index = following
