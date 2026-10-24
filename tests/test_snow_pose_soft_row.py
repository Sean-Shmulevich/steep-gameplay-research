import unittest
from engine.snow_pose_soft_row import soft_pose_row_parameters
from reference.central_impulse import f32


class SoftRowTests(unittest.TestCase):
    def test_zero_branch_preserves_stiffness_without_count_division(self):
        r=soft_pose_row_parameters([1,2,3,4],[0]*4,1e-6,0)
        self.assertTrue(r['near_zero']);self.assertEqual(r['coefficient'],[1,2,3,4])
        self.assertEqual(r['angle_gain'],[f32(.4)]*4)

    def test_count_mask_and_equation(self):
        r=soft_pose_row_parameters([8]*4,[2]*4,.5,(2<<2)|0x80000003)
        self.assertEqual(r['extracted_count'],2)
        self.assertEqual(r['coefficient'],[f32(.05)]*4)
        self.assertEqual(r['angle_gain'],[f32(.8)]*4)
        with self.assertRaises(ValueError):soft_pose_row_parameters([8]*4,[2]*4,.5,0)

    def test_full_row_preserves_holes_and_negates_all_axis_lanes(self):
        import math,struct
        from engine.snow_pose_soft_row import build_soft_pose_row
        r=build_soft_pose_row(b'\xa5'*96,class_byte=0,base_row=3,class_count=2,row_region_offset=256,result_count=0xffffffff,stiffness=[8]*4,damping=[2]*4,context_scalar=.5,context_flags=8,axis=[0,0,1,-0.],reference=[1,0,0,0],target=[0,1,0,0],atan2=math.atan2)
        self.assertEqual(r['relative_offset'],256+(3+12)*16)
        self.assertEqual(r['next_result_count'],0)
        self.assertEqual(r['row'][:4],b'\xa5'*4)
        self.assertEqual(r['row'][8:16],b'\xa5'*8)
        self.assertEqual(r['row'][0x30:0x40],b'\xa5'*16)
        self.assertEqual(struct.unpack_from('<4I',r['row'],0x40),(0x80000000,0x80000000,0xbf800000,0))
