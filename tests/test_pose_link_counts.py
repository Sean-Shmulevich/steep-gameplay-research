import struct
import unittest
from engine.pose_link_counts import count_pose_link_rows
from engine.pose_solver_layout import plan_pose_solver_layout

class LinkCountTests(unittest.TestCase):
    def payload(self,count,enabled=True):
        p=bytearray(288);struct.pack_into('<I',p,0x110,count);p[0x114]=int(enabled);return p
    def run_counts(self,mode,metadata=0,counts=None):
        if counts is None:counts=[0]*25
        count_pose_link_rows(counts,[0,1],links={0:dict(flags84=0),1:dict(flags84=1,second_body=2,payload_count=5,payload_slots=[0,1,2,3,4])},
            bodies={2:dict(metadata_flags50=metadata)},payloads={0:self.payload(0),1:self.payload(1),2:self.payload(2),3:self.payload(4),4:self.payload(99,False)},mode=mode)
        return counts

    def test_zero_mode_counts_multi_payloads_separately(self):
        for bit in (0,0x8000):
            r=self.run_counts(0,bit);b=int(bool(bit));expected=[0]*25
            expected[b]=7;expected[4+b]=2;expected[6+b]=2
            self.assertEqual(r,expected)

    def test_nonzero_mode_is_full_settings_value(self):
        for mode in (1,3,4,0xffffffff):
            r=self.run_counts(mode);expected=[0]*25;expected[0]=7;expected[6]=14
            self.assertEqual(r,expected)

    def test_accumulation_wraps_and_preserves_other_categories(self):
        r=self.run_counts(1,counts=[0xffffffff]*25)
        self.assertEqual(r[0],6);self.assertEqual(r[6],13);self.assertEqual(r[12],0xffffffff)

    def test_counts_feed_layout_without_builder_counter_guessing(self):
        counts=self.run_counts(1);plan=plan_pose_solver_layout(counts,1)
        self.assertEqual(plan['category_starts'][6],7*7)
        self.assertEqual(plan['result_bytes'],21*16)

    def test_single_payload_prepass_matches_completed_builder(self):
        import json
        from pathlib import Path
        from engine.pose_link_builder_bench import inspect
        document=json.loads((Path(__file__).resolve().parents[1]/'engine/examples/pose_link_builder.json').read_text())
        payload=bytearray.fromhex(document['inputs']['payload_hex']);counts=[0]*25
        count_pose_link_rows(counts,[1],links={1:dict(flags84=1,second_body=2,payload_count=1,payload_slots=[3])},
            bodies={2:dict(metadata_flags50=0)},payloads={3:payload},mode=0)
        built=inspect(document)
        self.assertEqual(counts[0],built['final_counters']['primary_count'])
        self.assertEqual(counts[6],built['final_counters']['secondary_count'])
        self.assertEqual(sum(counts),built['final_counters']['result_count'])
