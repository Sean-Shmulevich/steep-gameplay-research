import struct
import unittest
from engine.pose_contact_reverse import reverse_contact_records


class ContactReverseTest(unittest.TestCase):
    def test_sign_bits_point_swap_and_identifier_preservation(self):
        records=bytearray(b'X'*48+struct.pack('<12I',0,0x80000000,0x7fc01234,99,1,2,3,123,4,5,6,456)+b'Y'*48)
        before=bytes(records)
        reverse_contact_records(records,1,1)
        self.assertEqual(struct.unpack_from('<12I',records,48),(0x80000000,0,0xffc01234,99,4,5,6,123,1,2,3,456))
        self.assertEqual(records[:48],before[:48]);self.assertEqual(records[96:],before[96:])
        reverse_contact_records(records,1,1)
        self.assertEqual(records,before)

    def test_empty_and_invalid_ranges(self):
        records=bytearray(b'X'*48)
        reverse_contact_records(records,1,0)
        self.assertEqual(records,b'X'*48)
        with self.assertRaises(ValueError):reverse_contact_records(records,1,1)
