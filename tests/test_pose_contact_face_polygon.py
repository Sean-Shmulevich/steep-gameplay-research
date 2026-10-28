import struct
import unittest
from engine.pose_contact_face_polygon import append_face_polygon


class FacePolygonTest(unittest.TestCase):
    frame = [[2, 0, 0], [0, 3, 0], [0, 0, -1], [10, 20, 30]]

    def storage(self, count=0):
        result = bytearray(b"X" * 0x810)
        struct.pack_into("<I", result, 0x800, count)
        return result

    def test_append_preserves_existing_records_and_unused_storage(self):
        output = self.storage(1)
        before = bytes(output)
        append_face_polygon(output, self.frame, [[1, 2, 3]], [0], 7, 9)
        self.assertEqual(struct.unpack_from("<3fI", output, 16), (12, 26, 27, 0x80009007))
        self.assertEqual(struct.unpack_from("<I", output, 0x800), (2,))
        self.assertEqual(output[:16], before[:16])
        self.assertEqual(output[32:0x800], before[32:0x800])
        self.assertEqual(output[0x804:], before[0x804:])

    def test_tag_wrap_and_truncated_orientation_bit(self):
        outputs = []
        for flipped in (False, True):
            output = self.storage()
            append_face_polygon(output, self.frame, [[0, 0, 0]], [0] * 65,
                                0xfffff123, 0xabcdef45, flipped)
            self.assertEqual(struct.unpack_from("<I", output, 12), (0x80f45123,))
            self.assertEqual(struct.unpack_from("<I", output, 63 * 16 + 12), (0xbff45123,))
            self.assertEqual(output[:16], output[64 * 16:65 * 16])
            outputs.append(output)
        self.assertEqual(*outputs)

    def test_full_storage_empty_append_and_overflow_guard(self):
        output = self.storage(128)
        before = bytes(output)
        append_face_polygon(output, self.frame, [], [], 0, 0)
        self.assertEqual(output, before)
        with self.assertRaises(ValueError):
            append_face_polygon(output, self.frame, [[0, 0, 0]], [0], 0, 0)
        self.assertEqual(output, before)
