import struct
import unittest
from engine.snow_pose_limit_row import build_pose_limit_row
from reference.central_impulse import f32


class LimitRowTests(unittest.TestCase):
    def test_branch_is_all_four_lanes_and_preserves_holes(self):
        args=dict(class_byte=0,base_row=0,class_count=0,row_region_offset=256,result_count=7,context_scalar=2,context_flags=0x08000000,axis=[1,2,3,4],angle=[1,1,1,-1],sign=[1]*4,bound=[0]*4)
        r=build_pose_limit_row(b'\xa5'*128,**args)
        self.assertFalse(r['ungained'])
        self.assertEqual(struct.unpack_from('<4f',r['row'],0x10),(f32(.8),f32(.8),f32(.8),f32(-.8)))
        self.assertEqual(r['row'][0x58:0x60],b'\xa5'*8)
        self.assertEqual(struct.unpack_from('<4f',r['row'],0x70),(-1,-2,-3,-4))
        args['angle']=[0]*4;args['context_flags']=0
        self.assertTrue(build_pose_limit_row(bytes(128),**args)['ungained'])

    def test_phase_gate_counter_wrap_and_signed_zero(self):
        args=dict(class_byte=255,base_row=7,class_count=0xffffffff,
                  row_region_offset=256,result_count=0xffffffff,
                  context_scalar=1,axis=[1]*4,angle=[-1]*4,
                  sign=[1]*4,bound=[0]*4)
        for flags in (0,0x08000000,0x10000000,0x18000000):
            r=build_pose_limit_row(b'\xa5'*112,context_flags=flags,**args)
            expected=f32(-.4) if flags==0x08000000 else -0.
            self.assertEqual(r['row'][0x10:0x20],struct.pack('<4f',*([expected]*4)))
            self.assertEqual(r['relative_offset'],256)
            self.assertEqual(r['next_class_count'],0)
            self.assertEqual(r['next_result_count'],0)
            self.assertEqual(r['row'][:4],b'\xa5'*4)
            self.assertEqual(r['row'][0x40:0x50],b'\xa5'*16)
