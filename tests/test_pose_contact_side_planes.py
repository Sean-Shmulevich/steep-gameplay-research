import struct
import unittest
from engine.pose_contact_side_planes import append_side_planes


class SidePlaneTest(unittest.TestCase):
    frame = [[2, 0, 0], [0, 3, 0], [0, 0, 4], [10, 20, 30]]
    vertices = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]

    def storage(self, count=0):
        result = bytearray(b'X' * 0x810)
        struct.pack_into('<I', result, 0x800, count)
        return result

    def test_closing_edge_order_transform_and_retained_bytes(self):
        output = self.storage(2)
        before = bytes(output)
        append_side_planes(output, self.frame, self.vertices, [0, 1, 2, 3], [0, 0, 7])
        planes = [struct.unpack_from('<4f', output, 32+i*16) for i in range(4)]
        self.assertEqual(planes, [(-2, 0, 0, -20), (0, -3, 0, -60),
                                  (2, 0, 0, 21), (0, 3, 0, 61)])
        self.assertEqual(struct.unpack_from('<I', output, 0x800), (6,))
        self.assertEqual(output[:32], before[:32])
        self.assertEqual(output[96:0x800], before[96:0x800])
        self.assertEqual(output[0x804:], before[0x804:])

    def test_invalid_capacity_and_empty_indices_preserve_storage(self):
        for count, indices in [(127, [0, 1, 2, 3]), (0, [])]:
            output = self.storage(count)
            before = bytes(output)
            with self.assertRaises(ValueError):
                append_side_planes(output, self.frame, self.vertices, indices, [0, 0, 1])
            self.assertEqual(output, before)

    def test_degenerate_first_edge_rejected(self):
        output = self.storage()
        before = bytes(output)
        with self.assertRaises(ValueError):
            append_side_planes(output, self.frame, self.vertices, [0, 0], [0, 0, 1])
        self.assertEqual(output, before)
