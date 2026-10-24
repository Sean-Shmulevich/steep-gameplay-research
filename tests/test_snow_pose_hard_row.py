import math
import struct
import unittest
from engine.snow_pose_hard_row import build_hard_pose_row
from reference.central_impulse import f32


class HardRowTests(unittest.TestCase):
    def test_gain_requires_exact_masked_phase_and_keeps_holes(self):
        args=dict(class_byte=255,base_row=2,class_count=3,row_region_offset=256,result_count=0xffffffff,context_scalar=.5,axis=[0,0,1,0],reference=[1,0,0,0],target=[0,1,0,0],atan2=math.atan2)
        for phase,gain in ((0,0.),(0x08000000,f32(.4)),(0x10000000,0.),(0x18000000,0.)):
            r=build_hard_pose_row(b'\xa5'*64,context_flags=phase|3,**args)
            self.assertEqual(r['gain'],gain)
            self.assertEqual(r['relative_offset'],480)
            self.assertEqual(r['next_result_count'],0)
            self.assertEqual(r['row'][0x30:],b'\xa5'*16)
            if gain==0:self.assertEqual(struct.unpack_from('<I',r['row'],0x10)[0],0x80000000)
