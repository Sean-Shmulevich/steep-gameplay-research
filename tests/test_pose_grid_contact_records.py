import struct
import unittest
from engine.pose_grid_contact_records import convert_grid_contact_records


class GridContactRecordsTest(unittest.TestCase):
    def test_bitwise_roles_tags_and_retained_fields(self):
        records=bytearray(b'X'*144)
        struct.pack_into('<12I',records,48,0,0x80000000,0x7fc01234,0xabcdef01,
                         1,2,3,0x12345678,4,5,6,99)
        before=bytes(records)
        convert_grid_contact_records(records,1,1,0xdeadbeef)
        self.assertEqual(struct.unpack_from('<12I',records,48),
                         (0x80000000,0,0xffc01234,0xabcdef01,4,5,6,0x12345678,1,2,3,0xdeadbeef))
        self.assertEqual(records[:48],before[:48])
        self.assertEqual(records[96:],before[96:])

    def test_double_conversion_restores_roles_but_replaces_identifier(self):
        records=bytearray(struct.pack('<12I',*range(12)))
        before=bytes(records)
        convert_grid_contact_records(records,0,1,90)
        convert_grid_contact_records(records,0,1,91)
        self.assertEqual(records[:44],before[:44])
        self.assertEqual(struct.unpack_from('<I',records,44),(91,))
        convert_grid_contact_records(records,1,0,0)
        with self.assertRaises(ValueError):convert_grid_contact_records(records,1,1,0)
