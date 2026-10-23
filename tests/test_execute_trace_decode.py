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
