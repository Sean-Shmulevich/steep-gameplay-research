import math
import unittest
from engine.snow_prepass_direction import slope_projection_direction


class PrepassDirectionTests(unittest.TestCase):
    def test_up_threshold_skips_services_and_unused_fields(self):
        def unused(*args):raise AssertionError('unexpected service')
        r=slope_projection_direction([0,0,1,0],None,None,None,None,
                                     unused,unused,unused,unused)
        self.assertEqual(r,{'direction':[0,0,1,0],'branch':'up'})

    def test_signed_inclination_rotation(self):
        r=slope_projection_direction([1,0,0,0],[0,1,0,0],None,1,1,
                                     math.acos,math.sin,math.cos,lambda n:1/math.sqrt(n))
        self.assertAlmostEqual(r['direction'][0],-1,places=6)
        self.assertAlmostEqual(r['direction'][2],0,places=6)

    def test_depth_equality_corrects_and_preserves_four_lane_geometry(self):
        r=slope_projection_direction([1,0,0,0],[0,1,0,0],[0,0,.5,.5],0,.03,
                                     math.acos,math.sin,math.cos,lambda n:1/math.sqrt(n))
        self.assertEqual(r['branch'],'corrected')
        self.assertAlmostEqual(r['direction'][2],3/math.sqrt(10),places=6)
        self.assertAlmostEqual(r['direction'][3],-1/math.sqrt(10),places=6)
