import struct
import unittest
from engine.pose_grid_height_query import query_grid_height


class GridHeightQueryTest(unittest.TestCase):
    def resource(self,orientation=0):
        r=bytearray(0xa0);r[0x58]=orientation
        struct.pack_into('<2H',r,0x68,2,2);struct.pack_into('<2f',r,0x70,1,1)
        struct.pack_into('<2f',r,0x88,1,1);struct.pack_into('<H',r,0x9c,1)
        return r

    def test_piecewise_height_and_orientation_zero_reversed_ids(self):
        r=self.resource();samples=[0,2,4,10]
        self.assertEqual(query_grid_height(r,samples,.75,.25),(3.5,1))
        self.assertEqual(query_grid_height(r,samples,.25,.75),(4.5,0))
        self.assertEqual(query_grid_height(r,samples,.5,.5),(5,0))
        r[0x58]=1
        self.assertEqual(query_grid_height(r,samples,.25,.25),(1.5,0))
        self.assertEqual(query_grid_height(r,samples,.75,.75),(6.5,1))

    def test_lower_boundary_rejected_and_id_retained(self):
        value,tri=query_grid_height(self.resource(),[0]*4,0,.5,123)
        self.assertLess(value,-1e38);self.assertEqual(tri,123)
        self.assertEqual(query_grid_height(self.resource(),[0]*4,2**-23,.5),(0,0))
