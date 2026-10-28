import struct
import unittest
from engine.pose_contact_polygon_clip import clip_polygon_planes


class PolygonPlanesTest(unittest.TestCase):
    def storage(self):
        data = b''.join(struct.pack('<3fI', *p) for p in
                        [(-1, -1, 0, 10), (1, -1, 0, 20), (1, 1, 0, 30), (-1, 1, 0, 40)])
        return bytearray(data+b'X'*(4112-len(data)))

    def test_successive_planes_and_retained_tail(self):
        output = self.storage()
        count = clip_polygon_planes(output, 4, [[1, 0, 0, 0], [0, 1, 0, 0]])
        self.assertEqual(count, 4)
        self.assertEqual([struct.unpack_from('<3fI', output, i*16) for i in range(4)],
                         [(-1, 0, 0, 40), (-1, -1, 0, 10), (0, -1, 0, 20), (0, 0, 0, 30)])
        self.assertEqual(output[64:], b'X'*(4112-64))

    def test_rejection_at_each_stage_preserves_caller(self):
        keep, reject = [1, 0, 0, 2], [1, 0, 0, -2]
        for planes in ([reject, keep], [keep, reject], [keep, reject, keep]):
            output = self.storage()
            before = bytes(output)
            self.assertEqual(clip_polygon_planes(output, 4, planes), 0)
            self.assertEqual(output, before)

    def test_one_plane_is_explicitly_outside_contract(self):
        output = self.storage()
        before = bytes(output)
        with self.assertRaises(ValueError):
            clip_polygon_planes(output, 4, [[1, 0, 0, 2]])
        self.assertEqual(output, before)
