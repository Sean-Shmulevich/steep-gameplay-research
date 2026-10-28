import unittest
from engine.pose_contact_shapes import box_contact_shape, triangle_contact_shape


class ContactShapesTest(unittest.TestCase):
    def test_box_edges_join_faces_that_contain_both_endpoints(self):
        shape = box_contact_shape([2, 3, 4])
        self.assertEqual(shape['vertices'][0], [2, -3, 4])
        for a,b,p,q in shape['edges']:
            for face in (p,q):
                self.assertIn(a, shape['face_indices'][face])
                self.assertIn(b, shape['face_indices'][face])
        for plane, indices in zip(shape['planes'], shape['face_indices']):
            for i in indices:
                self.assertEqual(sum(a*b for a,b in zip(plane[:3],shape['vertices'][i])),plane[3])

    def test_triangle_opposite_plane_offsets_and_winding(self):
        shape = triangle_contact_shape([0,0,2],[2,0,2],[0,3,2])
        self.assertEqual(shape['planes'], [[0,0,1,2],[0,0,-1,-2]])
        self.assertEqual(shape['face_indices'], [(0,1,2),(2,1,0)])
        with self.assertRaises(ValueError):
            triangle_contact_shape([0,0,0],[1,0,0],[2,0,0])
