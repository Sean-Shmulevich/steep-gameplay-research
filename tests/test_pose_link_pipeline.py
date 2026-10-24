import struct
import unittest
from engine.pose_link_pipeline import process_pose_link_record_group,paired_entry_flag

FRAME=dict(basis=[[1,0,0],[0,1,0],[0,0,1]],translation=[0,0,0])


class PipelineTests(unittest.TestCase):
    def records(self,n):
        rows=[]
        for i in range(n):
            r=bytearray(48);struct.pack_into('<3f',r,0,0,0,1)
            struct.pack_into('<3fI3fI',r,16,i%3,i//3,0,i,1,2,3,9)
            rows.append(bytes(r))
        return rows

    def run_group(self,p,records,flag):
        return process_pose_link_record_group(p,records,first_frame=FRAME,second_frame=FRAME,
            first_index=2,second_index=3,entry_flag=flag)

    def test_reduce_then_update_preserves_selected_ids_and_cache(self):
        p=bytearray(288);struct.pack_into('<I',p,0x110,4)
        for i in range(4):
            struct.pack_into('<I',p,0x2c+i*64,i);struct.pack_into('<I',p,0x40+i*64,100+i)
        records=self.records(9);before=bytes(p)
        r=self.run_group(p,records,True)
        self.assertEqual(bytes(p),before);self.assertEqual(r['count'],4)
        for i,selected in enumerate(r['selected_indices']):
            self.assertEqual(r['records'][i],records[selected])
            self.assertEqual(struct.unpack_from('<I',r['payload'],0x2c+64*i)[0],selected)
            self.assertEqual(struct.unpack_from('<I',r['payload'],0x40+64*i)[0],100+selected if selected<4 else 0)
        self.assertEqual(r['records'][4:],records[4:])

    def test_small_group_bypasses_selector_and_replaces_only_bit_zero(self):
        p=bytearray(288);p[0x114]=0xaf
        r=self.run_group(p,self.records(2),False)
        self.assertIsNone(r['selection']);self.assertEqual(r['selected_indices'],[0,1])
        self.assertEqual(r['payload'][0x114],0xae)

    def test_both_raw_flags_require_both_bits(self):
        for a in range(256):
            for b in (0,4,16,20,255):
                self.assertEqual(paired_entry_flag(a,b),(a&20)==20 and (b&20)==20)

    def test_empty_group_is_not_a_reached_caller_iteration(self):
        with self.assertRaises(ValueError):self.run_group(bytes(288),[],False)
