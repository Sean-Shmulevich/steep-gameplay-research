import unittest
from engine.pose_link_geometry import link_point_geometry
from engine.pose_link_primary_response import link_primary_response

FRAME=dict(basis=((1,0,0),(0,1,0),(0,0,1)),translation=(0,0,0))

class GeometryTests(unittest.TestCase):
    def test_offset_is_readded_in_world_frame(self):
        g=link_point_geometry(FRAME,FRAME,(3,4,5),(9,8,7),(1,2,3))
        self.assertEqual(g['first_arm'],[2,2,2])
        self.assertEqual(g['first_world'],[3,4,5])
        self.assertEqual(g['separation'],[6,4,2])

    def test_float32_offset_cancellation_must_not_be_simplified(self):
        g=link_point_geometry(FRAME,FRAME,(1,0,0),(0,0,0),(2**25,0,0))
        self.assertEqual(g['first_world'],[0,0,0])
        self.assertNotEqual(g['first_world'],[1,0,0])

    def test_basis_rows_are_scaled_then_summed(self):
        frame=dict(basis=((2,0,0),(1,3,0),(0,2,4)),translation=(5,6,7))
        g=link_point_geometry(frame,FRAME,(1,2,3),(0,0,0),(0,0,0))
        self.assertEqual(g['first_world'],[9,18,19])

    def test_geometry_feeds_primary_response(self):
        g=link_point_geometry(FRAME,FRAME,(0,0,1),(0,0,4),(0,0,0))
        r=link_primary_response(g['separation'],(0,0,1),opposite_motion_projection=0,
                               response=-2,combined40=1,offset1c=0,threshold20=0)
        self.assertEqual(r['response'],6)
