import struct
import unittest
from engine.pose_contact_sort import sort_contact_records,compare_contact_details


def record(key,identity):
    return struct.pack('<I',identity)+bytes(40)+struct.pack('<I',key)


class ContactSortTest(unittest.TestCase):
    def test_equal_keys_use_swap_order_not_stability(self):
        records=[record(7,i) for i in range(3)]
        sort_contact_records(records,key_width=32)
        self.assertEqual([struct.unpack_from('<I',r)[0] for r in records],[1,2,0])

    def test_full_key_comparison_preserves_signed_overflow(self):
        self.assertEqual(compare_contact_details(record(0,0),record(0xffffffff,1),32),1)
        self.assertEqual(compare_contact_details(record(0,0),record(0xffffffff,1),16),-65535)
        records=[record(0,0),record(0xffffffff,1)]
        sort_contact_records(records,key_width=32)
        self.assertEqual([struct.unpack_from('<I',r,44)[0] for r in records],[0xffffffff,0])

    def test_partition_boundary_retains_whole_records(self):
        for size in (0,1,8,9,500):
            records=[record(i,i+100) for i in reversed(range(size))]
            expected=list(reversed(records))
            sort_contact_records(records,key_width=16)
            self.assertEqual(records,expected)

    def test_invalid_width_or_record_size_rejected(self):
        with self.assertRaises(ValueError):sort_contact_records([bytes(47)],key_width=32)
        with self.assertRaises(ValueError):sort_contact_records([],key_width=8)
