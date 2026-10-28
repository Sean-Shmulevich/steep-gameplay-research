import struct
import unittest
from engine.pose_grid_height_contact import query_sampled_grid_contact


class SampledContactTest(unittest.TestCase):
    def resource(self,orientation):
        r=bytearray(0xa0);r[0x58]=orientation
        struct.pack_into('<2H',r,0x68,2,2);struct.pack_into('<2f',r,0x70,1,1)
        struct.pack_into('<2f',r,0x88,1,1);struct.pack_into('<H',r,0x9c,1)
        return r

    def test_interpolation_controls_contact_and_retains_query_id(self):
        frame=[[1,0,0],[0,1,0],[0,0,1],[0,0,0]]
        for orientation,expected_height,expected_id in [(0,3.5,1),(1,2.5,1)]:
            out=bytearray(b'X'*64)
            self.assertTrue(query_sampled_grid_contact(self.resource(orientation),[0,2,4,10],
                                                       frame,[.75,.25,2],.5,out))
            self.assertEqual(struct.unpack_from('<f',out,12),(2-expected_height-.5,))
            self.assertEqual(struct.unpack_from('<f',out,24),(expected_height+.5,))
            self.assertEqual(struct.unpack_from('<I',out,44),(expected_id,))
            self.assertEqual(out[48:],b'X'*16)

    def test_outside_grid_at_ordinary_height_rejects_without_writes(self):
        out=bytearray(b'X'*48)
        self.assertFalse(query_sampled_grid_contact(self.resource(0),[0]*4,
            [[1,0,0],[0,1,0],[0,0,1],[0,0,0]],[-1,.5,0],1,out))
        self.assertEqual(out,b'X'*48)
