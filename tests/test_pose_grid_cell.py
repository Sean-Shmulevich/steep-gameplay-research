import struct
import unittest
from engine.pose_grid_cell import grid_cell_geometry, grid_triangle_sample_indices, grid_triangle_vertices

class GridCellTest(unittest.TestCase):
    def resource(self,flip):
        r=bytearray(0xc0);r[0x58]=flip
        struct.pack_into('<H',r,0x68,3);struct.pack_into('<H',r,0x9c,2)
        struct.pack_into('<2f',r,0x70,2,-3);struct.pack_into('<2f',r,0x7c,10,20)
        return r

    def test_vertex_coordinates_and_both_diagonals(self):
        for flag,expected in [(0,[0,1,2,2,3,0]),(255,[0,1,3,1,2,3])]:
            r=self.resource(flag)
            vertices,indices=grid_cell_geometry(r,list(range(9)),1,1)
            self.assertEqual(vertices,[[12,17,4],[14,17,5],[14,14,8],[12,14,7]])
            self.assertEqual(indices,expected)
            ids=[4,5,8,7]
            for half in (0,1):
                self.assertEqual(grid_triangle_sample_indices(r,6+half),
                                 [ids[i] for i in indices[3*half:3*half+3]])

    def test_divisor_is_distinct_from_stride(self):
        r=self.resource(0);struct.pack_into('<H',r,0x9c,1)
        self.assertEqual(grid_triangle_sample_indices(r,2),[3,4,7])

    def test_authored_storage_guards(self):
        r=self.resource(0)
        for col,row in [(-1,0),(2,0),(0,2)]:
            with self.assertRaises(ValueError):grid_cell_geometry(r,list(range(9)),col,row)
        struct.pack_into('<H',r,0x9c,0)
        with self.assertRaises(ValueError):grid_triangle_sample_indices(r,0)

    def test_triangle_vertices_match_sample_identity_and_clear_fourth_lane(self):
        samples=[-0.,1,2,3,4,5,6,7,8]
        for flip in (0,1,255):
            r=self.resource(flip)
            for ident in range(8):
                vertices=grid_triangle_vertices(r,samples,ident)
                sample_ids=grid_triangle_sample_indices(r,ident)
                self.assertEqual([v[2] for v in vertices],[samples[i] for i in sample_ids])
                for v in vertices:self.assertEqual(struct.pack('<f',v[3]),bytes(4))
        with self.assertRaises(ValueError):grid_triangle_vertices(r,samples,8)
