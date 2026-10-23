import struct
import unittest
from engine.action_ownership_transition import update_ownership_record


class OwnershipTransitionTests(unittest.TestCase):
    def record(self, current, requested):
        data = bytearray(b'\xa5'*0xe8)
        for i in range(7):
            struct.pack_into('<Q', data, 0x40+8*i, current)
            struct.pack_into('<Q', data, 0x78+8*i, requested)
        return bytes(data)

    def test_held_owner_survives_empty_request(self):
        before = self.record(42, 0)
        self.assertEqual(update_ownership_record(before, held=True, pressed=False), before)
        after = update_ownership_record(before, held=False, pressed=False)
        self.assertEqual(struct.unpack_from('<Q', after, 8)[0], 42)
        self.assertEqual(struct.unpack_from('<Q', after, 0x40)[0], 0)

    def test_press_capture_precedes_replacement(self):
        before = self.record(42, 99)
        after = update_ownership_record(before, held=True, pressed=True)
        for offset, expected in ((8, 42), (0x40, 99), (0x78, 99), (0xb0, 42)):
            self.assertEqual(struct.unpack_from('<Q', after, offset)[0], expected)
        self.assertEqual(after[:8], before[:8])

    def test_press_capture_occurs_even_when_held_retains_owner(self):
        after = update_ownership_record(self.record(42, 0), held=True, pressed=True)
        self.assertEqual(struct.unpack_from('<Q', after, 0xb0)[0], 42)
        self.assertEqual(struct.unpack_from('<Q', after, 8)[0], 0xa5a5a5a5a5a5a5a5)
