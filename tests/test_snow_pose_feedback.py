import struct
import unittest
from engine.snow_pose_feedback import publish_pose_feedback
from engine.snow_pose_solver_counts import HARD_THRESHOLD


class FeedbackTests(unittest.TestCase):
    def test_combined_uses_only_first_index_and_preserves_missing(self):
        storage=bytearray(288)
        for off in (0x8c,0xa0,0xb4):struct.pack_into('<f',storage,off,HARD_THRESHOLD)
        args=dict(first_flags8=0,second_flags8=0,type_id=2,storage=storage,result_rows=[bytes(range(16))])
        self.assertEqual(publish_pose_feedback(b'\xaa'*12,indices=[0,99,100],**args)['output'],bytes(range(12)))
        r=publish_pose_feedback(b'\xaa'*12,indices=[0xffffffff,0,0],**args)
        self.assertEqual(r['output'],b'\xaa'*12);self.assertEqual(r['written'],[False]*3)

    def test_separate_and_gate_preserve_unwritten_words(self):
        r=publish_pose_feedback(b'\xaa'*12,first_flags8=0,second_flags8=None,type_id=2,storage=bytes(288),indices=[1,0xffffffff,0],result_rows=[b'\x11'*16,b'\x22'*16])
        self.assertEqual(r['output'],b'\x22'*4+b'\xaa'*4+b'\x11'*4)
        self.assertEqual(r['written'],[True,False,True])
        r=publish_pose_feedback(b'\xaa'*12,first_flags8=1,second_flags8=None,type_id=2)
        self.assertEqual(r['mode'],'skipped')
