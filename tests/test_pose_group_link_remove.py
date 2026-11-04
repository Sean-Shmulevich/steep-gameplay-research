import struct
import unittest
from engine.pose_group_link_remove import remove_pose_group_link


class GroupLinkRemoveTests(unittest.TestCase):
    ARR = 0x5000

    def fixture(self, n, capacity=None):
        ptrs = [0x9000 + 0x100 * i for i in range(n)]
        slots = bytearray(8 * (capacity or max(n, 1)))
        objects = {}
        for i, p in enumerate(ptrs):
            struct.pack_into('<Q', slots, i * 8, p)
            o = bytearray(0x100); struct.pack_into('<I', o, 0x80, i); objects[p] = o
        group = bytearray(0x100)
        struct.pack_into('<Q', group, 0x40, self.ARR); struct.pack_into('<I', group, 0x48, n)
        return group, ptrs, slots, objects

    def run_remove(self, n, which):
        group, ptrs, slots, objects = self.fixture(n)
        remove_pose_group_link(group, objects[ptrs[which]], objects=objects, slot_arrays={self.ARR: slots})
        return group, ptrs, slots, objects

    def test_middle_removal_moves_last_and_repairs_index(self):
        group, ptrs, slots, objects = self.run_remove(4, 1)
        self.assertEqual(struct.unpack_from('<I', group, 0x48)[0], 3)
        self.assertEqual(struct.unpack_from('<4Q', slots), (ptrs[0], ptrs[3], ptrs[2], ptrs[3]))
        self.assertEqual(struct.unpack_from('<I', objects[ptrs[1]], 0x80)[0], 0xFFFFFFFF)
        self.assertEqual(struct.unpack_from('<I', objects[ptrs[3]], 0x80)[0], 1)

    def test_second_to_last_removal_repairs_moved_last(self):
        group, ptrs, slots, objects = self.run_remove(3, 1)
        self.assertEqual(struct.unpack_from('<2Q', slots), (ptrs[0], ptrs[2]))
        self.assertEqual(struct.unpack_from('<I', objects[ptrs[2]], 0x80)[0], 1)

    def test_last_member_removal_needs_no_repair(self):
        group, ptrs, slots, objects = self.run_remove(3, 2)
        self.assertEqual(struct.unpack_from('<I', group, 0x48)[0], 2)
        self.assertEqual(struct.unpack_from('<I', objects[ptrs[2]], 0x80)[0], 0xFFFFFFFF)
        self.assertEqual([struct.unpack_from('<I', objects[p], 0x80)[0] for p in ptrs[:2]], [0, 1])

    def test_single_member_empties_group(self):
        group, ptrs, slots, objects = self.run_remove(1, 0)
        self.assertEqual(struct.unpack_from('<I', group, 0x48)[0], 0)
        self.assertEqual(struct.unpack_from('<I', objects[ptrs[0]], 0x80)[0], 0xFFFFFFFF)

    def test_first_removal_keeps_capacity_tail(self):
        group, ptrs, slots, objects = self.fixture(3, capacity=8)
        remove_pose_group_link(group, objects[ptrs[0]], objects=objects, slot_arrays={self.ARR: slots})
        self.assertEqual(struct.unpack_from('<2Q', slots), (ptrs[2], ptrs[1]))
        self.assertEqual(struct.unpack_from('<Q', slots, 16)[0], ptrs[2])  # inactive tail retained
        self.assertEqual(struct.unpack_from('<I', objects[ptrs[2]], 0x80)[0], 0)

    def test_detached_or_empty_is_rejected_without_mutation(self):
        group, ptrs, slots, objects = self.fixture(2)
        struct.pack_into('<I', objects[ptrs[0]], 0x80, 0xFFFFFFFF)
        before = (bytes(group), bytes(slots))
        with self.assertRaises(ValueError):
            remove_pose_group_link(group, objects[ptrs[0]], objects=objects, slot_arrays={self.ARR: slots})
        self.assertEqual((bytes(group), bytes(slots)), before)
        struct.pack_into('<I', group, 0x48, 0)
        with self.assertRaises(ValueError):
            remove_pose_group_link(group, objects[ptrs[0]], objects=objects, slot_arrays={self.ARR: slots})


if __name__ == '__main__':
    unittest.main()
