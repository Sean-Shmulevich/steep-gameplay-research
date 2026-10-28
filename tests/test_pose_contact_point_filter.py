import struct
import unittest
from engine.pose_contact_point_filter import filter_plane_points, remove_near_points


class PointFilterTest(unittest.TestCase):
    def test_plane_compaction_tags_distances_and_tail(self):
        points = bytearray(b''.join(struct.pack('<3fI', x, 0, 0, tag)
                                   for x, tag in [(2, 10), (-3, 20), (0, 30)]))
        before = bytes(points)
        distances = bytearray(b'X'*16)
        self.assertEqual(filter_plane_points(distances, points, 3, [1, 0, 0, 0]), 2)
        self.assertEqual(points[:32], before[16:48])
        self.assertEqual(points[32:], before[32:])
        self.assertEqual(struct.unpack_from('<2f', distances), (-3, 0))
        self.assertEqual(distances[8:], b'X'*8)

    def test_swap_removal_rechecks_replacement_and_moves_distance(self):
        points = bytearray(b''.join(struct.pack('<3fI', x, 0, 0, i)
                                   for i, x in enumerate([0, 0.25, 3, 0.5])))
        distances = bytearray(struct.pack('<4f', -1, -2, -3, -4))
        self.assertEqual(remove_near_points(distances, points, 4, 1), 2)
        self.assertEqual(struct.unpack_from('<3fI', points, 16), (3, 0, 0, 2))
        self.assertEqual(struct.unpack_from('<2f', distances), (-1, -3))

    def test_exact_radius_retained_and_empty_buffers_unchanged(self):
        points = bytearray(struct.pack('<3fI3fI', 0, 0, 0, 1, 1, 0, 0, 2))
        distances = bytearray(8)
        self.assertEqual(remove_near_points(distances, points, 2, 1), 2)
        self.assertEqual(filter_plane_points(bytearray(), bytearray(), 0, [1, 0, 0, 0]), 0)
