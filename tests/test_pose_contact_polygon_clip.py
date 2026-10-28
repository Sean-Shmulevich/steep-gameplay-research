import struct
import unittest
from engine.pose_contact_polygon_clip import clip_polygon_plane


class PolygonClipTest(unittest.TestCase):
    def test_intersections_inherit_outside_tags_and_tail_persists(self):
        source = b''.join(struct.pack('<3fI', *p) for p in
                          [(-1, -1, 0, 10), (1, -1, 0, 20), (1, 1, 0, 30), (-1, 1, 0, 40)])
        output = bytearray(b'X'*144)
        count = clip_polygon_plane(output, source, 4, [1, 0, 0, 0])
        self.assertEqual(count, 4)
        self.assertEqual([struct.unpack_from('<3fI', output, i*16) for i in range(count)],
                         [(-1, -1, 0, 10), (0, -1, 0, 20), (0, 1, 0, 30), (-1, 1, 0, 40)])
        self.assertEqual(output[64:], b'X'*80)

    def test_tolerance_keeps_original_point_without_projecting(self):
        for x, expected in [(0.5e-5, 1), (1e-5, 0), (0., 1), (-1e-5, 1)]:
            source = struct.pack('<3fI', x, 2, 3, 99)
            output = bytearray(b'X'*32)
            self.assertEqual(clip_polygon_plane(output, source, 1, [1, 0, 0, 0]), expected)
            self.assertEqual(output[:16], source if expected else b'X'*16)

    def test_capacity_guard_does_not_write(self):
        source = struct.pack('<3fI', 0, 0, 0, 1)
        output = bytearray(b'X'*16)
        with self.assertRaises(ValueError):
            clip_polygon_plane(output, source, 1, [1, 0, 0, 0])
        self.assertEqual(output, b'X'*16)
