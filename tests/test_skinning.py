import unittest
from reference import skinning as s

I=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
def pose(x=0):return {'translation':[x,0,0],'quaternion_xyzw':[0,0,0,1]}

class SkinningTests(unittest.TestCase):
    def test_missing_remap(self):
        self.assertEqual(s.remap_mesh_joints([None,7,3,None]),[7,7,3,7])
        self.assertEqual(s.remap_mesh_joints([None,None]),[])
    def test_scale_order_and_origin(self):
        bind=[row[:] for row in I];bind[0][3]=-2
        palette=s.native_skinning_palette([bind],[0],[pose(5)],pose(10),(1,0,0),2)
        self.assertEqual(s.transform_rows(palette[0],(1,0,0)),(14,0,0))
    def test_absent_pose_ignores_origin_and_bind(self):
        palette=s.native_skinning_palette([I],[None],None,pose(10),(20,0,0),2)
        self.assertEqual(s.transform_rows(palette[0],(1,2,3)),(2,4,6))
    def test_missing_index_branch(self):
        with self.assertRaises(ValueError):s.native_skinning_palette([I],[None],[pose()],pose(),(0,0,0),1)
        palette=s.native_skinning_palette([I],[None],[pose()],pose(),(1,0,0),2)
        self.assertEqual(s.transform_rows(palette[0],(1,0,0)),(3,0,0))
    def test_no_weight_normalization(self):
        self.assertEqual(s.shader_skin_position((1,2,3),[1,1,0,0],[0]*4,[I[:3]],4),(2,4,6))
    def test_zero_weight_still_reads_index(self):
        with self.assertRaises(IndexError):s.shader_skin_position((1,0,0),[1,0,0,0],[0,99,0,0],[I[:3]],4)
    def test_missing_anchor_retains_output(self):
        previous=object()
        self.assertIs(s.anchored_render_matrix(None,I,previous_output=previous),previous)
