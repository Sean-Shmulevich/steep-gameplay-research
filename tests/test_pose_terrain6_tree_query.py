"""Tests for engine.pose_terrain6_tree_query (0x1952b20 / 0x19507f0 / 0x1952f20) with authored trees.

Native agreement is in native/snow_host/pose_terrain6_leaves_validation.json; these fixtures are
small synthetic trees, not game data.
"""
import struct
import unittest

from engine.pose_pair_link_worker import PoseFlatMemory
from engine import pose_terrain6_tree_query as tq

TREE, NODES, OUT = 0x1000, 0x10000, 0x80000
NAN = 0x7FC00000


def fb(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def box(lo, hi):
    return [fb(x) for x in list(lo) + list(hi)]


def node(c0, c1, qmin=(0, 0, 0), qmax=(0, 0, 0), select=0):
    """c0/c1: ('leaf', id) or ('node', index). select: flag bits 2..7."""
    flags = select & 0xFC
    ids = []
    for ci, (kind, v) in enumerate((c0, c1)):
        if kind == 'leaf':
            flags |= 1 << ci
        ids.append(v)
    return bytes(qmin) + bytes([flags]) + bytes(qmax) + b'\0' + struct.pack('<HH', *ids)


def memory(nodes, ext=(8, 8, 8), mn=(0, 0, 0)):
    hdr = bytearray(0x20)
    struct.pack_into('<3f', hdr, 0, *ext)
    struct.pack_into('<3f', hdr, 0xC, *mn)
    struct.pack_into('<Q', hdr, 0x18, NODES)
    raw = b''.join(nodes) + bytes(16)
    return PoseFlatMemory({TREE: hdr, NODES: bytearray(raw), OUT: bytearray(b'\xee' * 0x10000)})


EVERYTHING = box((-1, -1, -1), (9, 9, 9))


def L(i): return ('leaf', i)
def N(i): return ('node', i)


def balanced(leaves):
    """Index 0 is the root; children laid out breadth first; all boxes equal the root box."""
    nodes, pending, next_index = [], [(0, list(range(leaves)))], 1
    out = {}
    while pending:
        idx, ids = pending.pop(0)
        kids = []
        for part in (ids[:len(ids) // 2], ids[len(ids) // 2:]):
            if len(part) == 1:
                kids.append(L(part[0]))
            else:
                kids.append(N(next_index))
                pending.append((next_index, part))
                next_index += 1
        out[idx] = node(*kids)
    return [out[i] for i in range(len(out))]


class TreeQuery(unittest.TestCase):
    def test_root_leaves_in_child_order(self):
        mem = memory([node(L(7), L(3))])
        self.assertEqual(tq.tree_query(mem, TREE, EVERYTHING, 10, OUT), [7, 3])
        self.assertEqual(bytes(mem.view(OUT, 6)), struct.pack('<HH', 7, 3) + b'\xee\xee')

    def test_quantized_child_boxes_and_rejection(self):
        # x: child 0 keeps [0, hi] with hi = 8 - (128/255)*8, child 1 keeps [lo, 8] with lo = (128/255)*8.
        n = node(L(1), L(2), qmin=(128, 0, 0), qmax=(128, 0, 0), select=0x20)
        mem = memory([n])
        self.assertEqual(tq.tree_query(mem, TREE, box((6, 1, 1), (7, 2, 2)), 10), [2])
        self.assertEqual(tq.tree_query(mem, TREE, box((1, 1, 1), (2, 2, 2)), 10), [1])
        self.assertEqual(tq.tree_query(mem, TREE, box((3.99, 1, 1), (4.01, 2, 2)), 10), [])      # the gap
        self.assertEqual(tq.tree_query(mem, TREE, box((3.9, 1, 1), (4.1, 2, 2)), 10), [1, 2])
        flags, ids, boxes = tq.decode_children(mem, NODES, (tq.vmask(tq._vec(mem, TREE)),
                                                            tq.vmask(tq._vec(mem, TREE + 0xC)), 0), False, 'sse')
        c = struct.unpack('<f', struct.pack('<I', tq.INV_255))[0]
        hi = struct.unpack('<f', struct.pack('<I', boxes[0][1][0]))[0]
        self.assertAlmostEqual(hi, 8 - 128 * c * 8, places=5)
        self.assertEqual(boxes[1][1][0], fb(8.0))          # child 1 keeps the parent max on x

    def test_touching_boxes_are_not_rejected(self):
        mem = memory([node(L(1), L(2))])
        self.assertEqual(tq.tree_query(mem, TREE, box((8, 8, 8), (9, 9, 9)), 10), [1, 2])
        self.assertEqual(tq.tree_query(mem, TREE, box((8.001, 0, 0), (9, 9, 9)), 10), [])

    def test_capacity_is_checked_after_each_write(self):
        mem = memory([node(L(1), L(2))])
        self.assertEqual(tq.tree_query(mem, TREE, EVERYTHING, 1), [1])
        self.assertEqual(tq.tree_query(mem, TREE, EVERYTHING, 0), [1])            # signed, after the write
        self.assertEqual(tq.tree_query(mem, TREE, EVERYTHING, 0xFFFFFFFF), [1])   # -1
        self.assertEqual(tq.tree_query(mem, TREE, EVERYTHING, 2), [1, 2])

    def test_register_slots_are_visited_before_the_fifo(self):
        # root -> L(1), R(2); L -> L1(3), L2(4); R -> R1(5), leaf r; L1 -> L1a(6), leaf x;
        # L2 -> y, z; R1 -> s, t; L1a -> p, q.
        r, x, y, z, s, t, p, q = range(10, 18)
        nodes = [node(N(1), N(2)), node(N(3), N(4)), node(N(5), L(r)), node(N(6), L(x)),
                 node(L(y), L(z)), node(L(s), L(t)), node(L(p), L(q))]
        trace = {}
        ids = tq.tree_query(memory(nodes), TREE, EVERYTHING, 100, trace=trace)
        self.assertEqual(ids, [r, x, y, z, p, q, s, t])      # breadth first would give s, t before p, q
        self.assertEqual((trace['singles'], trace['pairs'], trace['pushes']), (1, 3, 1))
        # truncation follows the same order
        self.assertEqual(tq.tree_query(memory(nodes), TREE, EVERYTHING, 5), [r, x, y, z, p])

    def test_queue_growth_events(self):
        trace = {}
        nodes = balanced(1200)
        ids = tq.tree_query(memory(nodes), TREE, EVERYTHING, 0x7FFFFFFF, trace=trace)
        self.assertEqual(sorted(ids), list(range(1200)))
        self.assertGreater(trace['pushes'], 0x100)
        self.assertEqual(trace['growths'][0], (0x100, 0x200))
        self.assertEqual(trace['allocations'][0], ('alloc', 0x200 * 0x30))
        self.assertTrue(all(a[0] == 'realloc' for a in trace['allocations'][1:-1]))
        self.assertEqual(trace['allocations'][-1], ('free',))
        small = {}
        tq.tree_query(memory(balanced(64)), TREE, EVERYTHING, 0x7FFFFFFF, trace=small)
        self.assertEqual(small['allocations'], [])

    def test_nan_box_lane_never_rejects_and_inverted_box_rejects(self):
        mem = memory([node(L(1), L(2))])
        words = box((100, 100, 100), (200, 200, 200))
        words[0] = NAN
        self.assertEqual(tq.tree_query(mem, TREE, words, 10), [])        # y and z still reject
        words = [NAN] * 6
        self.assertEqual(tq.tree_query(mem, TREE, words, 10), [1, 2])
        self.assertEqual(tq.tree_query(mem, TREE, box((5, 5, 5), (4, 4, 4)), 10), [1, 2])   # inside the root
        self.assertEqual(tq.tree_query(mem, TREE, box((9, 9, 9), (-1, -1, -1)), 10), [])

    def test_zero_extent_root(self):
        mem = memory([node(L(1), L(2), qmin=(200, 200, 200), qmax=(200, 200, 200), select=0xFC)], ext=(0, 0, 0))
        self.assertEqual(tq.tree_query(mem, TREE, box((0, 0, 0), (0, 0, 0)), 10), [1, 2])
        self.assertEqual(tq.tree_query(mem, TREE, box((1e-6, 0, 0), (1, 1, 1)), 10), [])

    def test_service_binding(self):
        mem = memory([node(L(4), L(5))])
        traces = []
        query = tq.service(mem, traces=traces)
        self.assertEqual(query(TREE, EVERYTHING, 0x80), [4, 5])
        self.assertEqual(traces[0]['ids'], [4, 5])
        self.assertEqual(traces[0]['capacity'], 0x80)


if __name__ == '__main__':
    unittest.main()
