import struct
import unittest

from engine import pose_broadphase_pair_lists as bp


class Mem:
    def __init__(self):
        self.b = {}

    def put(self, addr, raw):
        self.b[addr] = bytearray(raw)

    def read(self, addr, size):
        for base, raw in self.b.items():
            if base <= addr and addr + size <= base + len(raw):
                return bytes(raw[addr - base:addr - base + size])
        raise KeyError(hex(addr))


def make(added, removed, swap=False):
    mem = Mem()
    obj = bytearray(0x200)
    hdr_a, hdr_b = 0x5000, 0x6000
    cur = hdr_b if swap else hdr_a
    for hdr, rows, data in ((hdr_a, added if not swap else [], 0x7000),
                            (hdr_b, added if swap else [], 0x8000)):
        mem.put(hdr, struct.pack('<QII', data, len(rows), 32))
        mem.put(data, b''.join(struct.pack('<QQQ', *r) for r in rows) or b'\0')
    struct.pack_into('<Q', obj, 0xF8, cur)
    struct.pack_into('<Q', obj, 0x118, 0x9000)
    struct.pack_into('<I', obj, 0x120, len(removed))
    mem.put(0x9000, b''.join(struct.pack('<QQQ', *r) for r in removed) or b'\0')
    return bytes(obj), mem


class BroadphasePairListTests(unittest.TestCase):
    def test_counts_and_arrays(self):
        added = [(1, 2, 3), (4, 5, 6)]
        removed = [(7, 8, 9)]
        obj, mem = make(added, removed)
        self.assertEqual(bp.added_pair_count(obj, mem.read), 2)
        self.assertEqual(bp.added_pair_array(obj, mem.read), 0x7000)
        self.assertEqual(bp.removed_pair_count(obj), 1)
        self.assertEqual(bp.removed_pair_array(obj), 0x9000)
        self.assertEqual(bp.controller_pair_lists(obj, mem.read), (removed, added))

    def test_swapped_header_selects_other_buffer(self):
        added = [(10, 11, 12)]
        obj, mem = make(added, [], swap=True)
        self.assertEqual(bp.added_pair_array(obj, mem.read), 0x8000)
        self.assertEqual(bp.controller_pair_lists(obj, mem.read), ([], added))

    def test_empty(self):
        obj, mem = make([], [])
        self.assertEqual(bp.controller_pair_lists(obj, mem.read), ([], []))


if __name__ == '__main__':
    unittest.main()
