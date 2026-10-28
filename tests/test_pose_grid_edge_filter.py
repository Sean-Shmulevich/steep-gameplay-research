import struct
import unittest
from engine.pose_grid_edge_filter import reject_grid_edge

class EdgeFilterTest(unittest.TestCase):
    def setUp(self):
        self.r=bytearray(0xc0)
        struct.pack_into('<2H',self.r,0x68,3,3)
        struct.pack_into('<2f',self.r,0x70,1,1)
        self.samples=[0.]*9

    def test_direction_threshold_and_boundary_fallback(self):
        def check(direction,threshold):
            return reject_grid_edge(self.r,self.samples,0,1,[0,0,0],[1,0,0],direction,threshold)
        self.assertTrue(check([0,1,0],[.1]*4))
        self.assertFalse(check([0,-1,0],[.1]*4))
        self.assertFalse(check([1,0,0],[0.]*4))
        self.assertFalse(check([0,1,0],[2.]*4))
        self.assertFalse(check([0,1,0],[.1,2,.1,.1]))

    def test_authored_degenerate_and_unsupported_guards(self):
        with self.assertRaises(ValueError):
            reject_grid_edge(self.r,self.samples,0,8,[0,0,0],[2,2,0],[0,1,0],[.1]*4)
        with self.assertRaises(ValueError):
            reject_grid_edge(self.r,self.samples,0,1,[0,0,0],[0,0,0],[0,1,0],[.1]*4)
