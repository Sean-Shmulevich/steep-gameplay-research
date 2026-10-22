import struct
import unittest
from engine.replay_columns import decode_columns


class ReplayColumnsTests(unittest.TestCase):
    def test_literal_and_runs_transpose_to_records(self):
        data=struct.pack('<I',3)+bytes([1,10,20,30,40, 0,7,3,8,1, 2,5,6,7,8])
        result=decode_columns(data+b'tail',4)
        self.assertEqual(result['data'],bytes([10,7,5,20,7,6,30,7,7,40,8,8]))
        self.assertEqual(result['consumed'],len(data))

    def test_zero_run_count_means_256_and_partial_last_run_is_allowed(self):
        data=struct.pack('<I',1)+bytes([0,9,0,10,1])
        self.assertEqual(decode_columns(data,257)['data'],bytes([9])*256+bytes([10]))
        self.assertEqual(decode_columns(data,3)['data'],bytes([9])*3)
        self.assertEqual(decode_columns(data,3)['consumed'],7)

    def test_truncation_and_allocation_bounds(self):
        valid=struct.pack('<I',1)+bytes([1,2,3])
        for end in range(len(valid)):
            with self.subTest(end=end),self.assertRaises(ValueError):decode_columns(valid[:end],2)
        with self.assertRaises(ValueError):decode_columns(struct.pack('<I',0xffffffff),2)
        with self.assertRaises(ValueError):decode_columns(valid,2,max_output=1)
        with self.assertRaises(ValueError):decode_columns(valid,True)
        self.assertEqual(decode_columns(struct.pack('<I',0),3)['data'],b'')
