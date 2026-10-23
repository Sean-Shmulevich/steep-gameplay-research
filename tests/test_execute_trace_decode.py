import struct
import unittest

from scripts.decode_execute_trace import decode


class ExecuteTraceDecodeTests(unittest.TestCase):
    def test_all_phases(self):
        for phase in range(6):
            with self.subTest(phase=phase):
                result = decode(struct.pack("<5i", 1, 2, 1, phase, 0))
                self.assertEqual(result["phase"], phase)
                self.assertFalse(result["atomic_snapshot"])

    def test_rejects_wrong_size_version_and_phase(self):
        for data in (b"", b"0" * 21, struct.pack("<5i", 2, 0, 0, 0, 0),
                     struct.pack("<5i", 1, 0, 0, 6, 0)):
            with self.subTest(data=data), self.assertRaises(ValueError):
                decode(data)

    def test_preserves_unsigned_error(self):
        result = decode(struct.pack("<5i", 1, 1, 1, 5, -1))
        self.assertEqual(result["restore_error"], 0xffffffff)

    def test_v2_published_and_incomplete_events(self):
        data = bytearray(536)
        struct.pack_into("<6i", data, 0, 2, 2, 0, 0, 0, 8)
        struct.pack_into("<8Q", data, 24, 1, 0x80000003, 0, 0, 2, 0, 0, 0x1234)
        struct.pack_into("<8Q", data, 88, 0, 0, 0, 0, 999, 0, 0, 0)
        result = decode(data)
        self.assertEqual(len(result["exceptions"]), 1)
        self.assertEqual(result["exceptions"][0]["reason"], "not_access_violation")
        self.assertEqual(result["exceptions"][0]["instruction"], "0x1234")
        self.assertTrue(result["private_addresses"])

    def test_v2_rejects_capacity_and_published_invalid_reason(self):
        data = bytearray(536)
        struct.pack_into("<6i", data, 0, 2, 0, 0, 0, 0, 9)
        with self.assertRaises(ValueError):
            decode(data)
        struct.pack_into("<i", data, 20, 8)
        struct.pack_into("<8Q", data, 24, 1, 0, 0, 0, 8, 0, 0, 0)
        with self.assertRaises(ValueError):
            decode(data)
