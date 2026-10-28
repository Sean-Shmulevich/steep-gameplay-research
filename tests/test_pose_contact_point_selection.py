import struct
import unittest
from engine.pose_contact_point_filter import select_contact_points


class PointSelectionTest(unittest.TestCase):
    def test_four_extrema_gather_tags_and_corresponding_separations(self):
        vertices = [(-2, -2, -1), (2, -2, -2), (2, 2, -3), (-2, 2, -4), (0, 0, -5)]
        points = bytearray(b''.join(struct.pack('<3fI', *v, 100+i)
                                   for i, v in enumerate(vertices))+b'X'*16)
        original = bytes(points)
        distances = bytearray(b'Y'*32)
        count = select_contact_points(distances, points, 5, [0, 0, 1, 0], True)
        self.assertEqual(count, 4)
        self.assertEqual(points[:64], b''.join(original[i*16:(i+1)*16] for i in [3, 1, 0, 2]))
        self.assertEqual(struct.unpack_from('<4f', distances), (-4, -2, -1, -3))
        self.assertEqual(points[64:], original[64:])
        self.assertEqual(struct.unpack_from('<f', distances, 16), (-5,))
        self.assertEqual(distances[20:], b'Y'*12)

    def test_reduction_gate_does_not_require_normal_when_four_remain(self):
        original = b''.join(struct.pack('<3fI', x, 0, 0, x) for x in range(4))
        points = bytearray(original)
        distances = bytearray(16)
        self.assertEqual(select_contact_points(distances, points, 4, [0, 0, 0, 0], True), 4)
        self.assertEqual(points, original)
