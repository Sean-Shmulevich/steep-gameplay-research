import struct
import unittest
from engine.pose_grid_candidates import write_grid_triangle_candidates

class CandidatesTest(unittest.TestCase):
    def setUp(self):
        self.r=bytearray(0xc0);struct.pack_into('<2H',self.r,0x9c,2,2)
        struct.pack_into('<2f',self.r,0x70,1,1)
        struct.pack_into('<6f',self.r,0x7c,0,0,-1,2,2,1)

    def test_capacity_can_split_triangle_pair(self):
        out=bytearray(b'X'*40)
        count=write_grid_triangle_candidates(self.r,[0,0,-1,2,2,1],out,3)
        self.assertEqual(count,3);self.assertEqual(struct.unpack_from('<3I',out),(0,1,2))
        self.assertEqual(out[12:],b'X'*28)

    def test_exact_boundary_and_height_rejection(self):
        out=bytearray(b'X'*40)
        self.assertEqual(write_grid_triangle_candidates(self.r,[0,0,2,2,2,3],out,8),0)
        self.assertEqual(out,b'X'*40)
        self.assertEqual(write_grid_triangle_candidates(self.r,[1,1,1,1,1,1],out,8),2)
        self.assertEqual(struct.unpack_from('<2I',out),(6,7))
        with self.assertRaises(ValueError):write_grid_triangle_candidates(self.r,[0]*6,out,0)
