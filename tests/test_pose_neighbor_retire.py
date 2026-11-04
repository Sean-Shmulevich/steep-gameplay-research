import struct
import unittest

from engine.pose_neighbor_retire import retire_pose_neighbor_records, clear_pose_neighbor_record
from engine.pose_endpoint_rings import attach_pose_endpoint_rings, detach_pose_endpoint_rings
from engine.pose_body_connectivity_retire import reserve_pose_pointer_vector

NODES, OWNER, A, B = 0x100, 0x200, 0x300, 0x400


class Allocator:
    def __init__(self, arrays): self.arrays = arrays; self.next = 0x9000; self.log = []
    def allocate(self, size, align, tag):
        p = self.next; self.next += 0x1000; self.arrays[p] = bytearray(size); self.log.append(('allocate', size)); return p
    def reallocate(self, old, size, align, tag):
        p = self.next; self.next += 0x1000; src = self.arrays[old][:size]
        self.arrays[p] = bytearray(src) + bytearray(size - len(src)); self.log.append(('reallocate', size)); return p
    def release(self, p): self.log.append(('release', p))


def fixture(states, divisor_slots=(OWNER,)):
    """Balanced 3-node tree (keys 10,20,30 -> slots 1,0,2) or smaller; values 0x1000+0x100*slot."""
    n = len(states)
    nodes = bytearray(32 * max(n, 1))
    layout = {1: [(-1, -1, -1)], 2: [(1, -1, -1), (-1, -1, 0)], 3: [(1, 2, -1), (-1, -1, 0), (-1, -1, 0)]}[n] if n else []
    keys = {1: [10], 2: [20, 10], 3: [20, 10, 30]}.get(n, [])
    records = {}
    for s, (l, r, p) in enumerate(layout):
        value = 0x1000 + 0x100 * s
        struct.pack_into('<iiiBBxxQQ', nodes, s * 32, l, r, p, 0, 0, value, keys[s])
        rec = bytearray(0x60); struct.pack_into('<QQ', rec, 8, A, B); struct.pack_into('<I', rec, 0x50, 3); struct.pack_into('<I', rec, 0x58, states[s])
        records[value] = rec
    provider = bytearray(0x100)
    struct.pack_into('<QII', provider, 0x38, NODES, n, 0); struct.pack_into('<ii', provider, 0x4C, 0 if n else -1, -1)
    for i, o in enumerate(divisor_slots): struct.pack_into('<Q', provider, 0x70 + 8 * i, o)
    bodies = {A: bytearray(0xA0), B: bytearray(0xA0)}
    for t in records: attach_pose_endpoint_rings(t, 0, records=records, bodies=bodies)
    return provider, nodes, records, bodies


def run(provider, nodes, records, bodies, divisor, owners):
    arrays = {}; alloc = Allocator(arrays); order = []
    def detach(t, sel):
        order.append(t); detach_pose_endpoint_rings(t, sel, records=records, bodies=bodies)
    retire_pose_neighbor_records(provider, divisor, node_arrays={NODES: nodes}, records=records, queue_owners=owners,
                                 queue_arrays=arrays, detach=detach,
                                 reserve=lambda d, c: reserve_pose_pointer_vector(d, c, allocator=alloc))
    return order, arrays, alloc


class NeighborRetireTests(unittest.TestCase):
    def test_empty_tree_does_nothing_and_never_divides(self):
        provider, nodes, records, bodies = fixture([])
        before = bytes(provider)
        self.assertEqual(run(provider, nodes, records, bodies, 0, {})[0], [])
        self.assertEqual(bytes(provider), before)

    def test_in_order_sweep_retires_only_state4_and_queues_round_robin(self):
        provider, nodes, records, bodies = fixture([4, 4, 4], (OWNER, OWNER + 0x100))
        owners = {OWNER: bytearray(0x60), OWNER + 0x100: bytearray(0x60)}
        order, arrays, alloc = run(provider, nodes, records, bodies, 2, owners)
        self.assertEqual(order, [0x1100, 0x1000, 0x1200])        # keys 10, 20, 30
        q0 = struct.unpack_from('<QII', owners[OWNER], 0x48); q1 = struct.unpack_from('<QII', owners[OWNER + 0x100], 0x48)
        self.assertEqual((q0[1], q0[2], q1[1]), (2, 8, 1))
        self.assertEqual(struct.unpack_from('<2Q', arrays[q0[0]], 0), (0x1100, 0x1200))
        self.assertEqual(struct.unpack_from('<Q', arrays[q1[0]], 0)[0], 0x1000)
        self.assertEqual(struct.unpack_from('<i', provider, 0x4C)[0], -1)
        for r in records.values():
            self.assertEqual(r[8:0x40], bytes(0x38)); self.assertEqual(struct.unpack_from('<I', r, 0x50)[0], 0)
        self.assertEqual(struct.unpack_from('<Q', bodies[A], 0x88)[0], 0)

    def test_other_states_stay_in_tree_and_rings(self):
        provider, nodes, records, bodies = fixture([0, 4, 5])
        owners = {OWNER: bytearray(0x60)}
        order, _, _ = run(provider, nodes, records, bodies, 1, owners)
        self.assertEqual(order, [0x1100])
        self.assertEqual(struct.unpack_from('<ii', provider, 0x40), (2, 1))  # slot1 joins the free list
        self.assertEqual(struct.unpack_from('<Q', records[0x1000], 8)[0], A)

    def test_two_child_removal_keeps_successor(self):
        """Root (two children) is removed after its predecessor was visited; the right child is still swept."""
        provider, nodes, records, bodies = fixture([4, 0, 4])
        order, _, _ = run(provider, nodes, records, bodies, 1, {OWNER: bytearray(0x60)})
        self.assertEqual(order, [0x1000, 0x1200])

    def test_zero_divisor_faults_after_first_queued_record(self):
        provider, nodes, records, bodies = fixture([0, 4, 4])
        owners = {OWNER: bytearray(0x60)}
        with self.assertRaises(ZeroDivisionError):
            run(provider, nodes, records, bodies, 0, owners)
        self.assertEqual(struct.unpack_from('<I', owners[OWNER], 0x50)[0], 1)

    def test_clear(self):
        r = bytearray(range(0x60)); clear_pose_neighbor_record(r)
        self.assertEqual((r[8:0x18], struct.unpack_from('<I', r, 0x50)[0]), (bytes(16), 0))
        self.assertEqual(r[0x18:0x50], bytes(range(0x18, 0x50)))


if __name__ == '__main__':
    unittest.main()
