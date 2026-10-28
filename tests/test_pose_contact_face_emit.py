import struct
import unittest
from engine.pose_contact_face_emit import emit_face_contacts


class FaceEmitTest(unittest.TestCase):
    frame = [[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 0, 0]]
    shape = dict(vertices=[[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0]],
                 planes=[[0, 0, 1, 0], [0, 0, -1, 0]],
                 face_indices=[[0, 1, 2, 3], [0, 1, 2, 3]])

    def test_orientation_linear_separation_and_capacity(self):
        incident = [*self.frame[:3], [0, 0, -2]]
        for flipped in (False, True):
            output = bytearray(b'X'*64)
            self.assertEqual(emit_face_contacts(output, 1, self.frame, self.shape,
                                               incident, self.shape, 0, False, flipped), 1)
            self.assertEqual(struct.unpack_from('<3f', output), (0, 0, -1 if flipped else 1))
            self.assertEqual(struct.unpack_from('<f', output, 12), (-2,))
            self.assertEqual(struct.unpack_from('<3f', output, 16), (-1, -1, -2 if flipped else 0))
            self.assertEqual(struct.unpack_from('<3f', output, 32), (-1, -1, 0 if flipped else -2))
            self.assertEqual(struct.unpack_from('<I', output, 28), (0,))
            self.assertEqual(struct.unpack_from('<I', output, 44), (0xffff0000,))
            self.assertEqual(output[48:], b'X'*16)

    def test_separated_face_and_zero_capacity_preserve_output(self):
        for height, capacity in [(2, 4), (-2, 0)]:
            output = bytearray(b'X'*192)
            self.assertEqual(emit_face_contacts(output, capacity, self.frame, self.shape,
                                               [*self.frame[:3], [0, 0, height]], self.shape, 0), 0)
            self.assertEqual(output, b'X'*192)
