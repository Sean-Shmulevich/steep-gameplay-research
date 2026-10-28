import unittest
from engine.pose_contact_face_query import query_contact_faces
from engine.pose_contact_axis_selection import select_contact_axis

class FaceQueryTest(unittest.TestCase):
    frame=[[1,0,0],[0,1,0],[0,0,1],[0,0,0]]
    def test_first_positive_and_earliest_tie(self):
        f=self.frame;v={'vertices':[[0,0,0]]}
        self.assertEqual(query_contact_faces(f,{'planes':[[1,0,0,-1],[1,0,0,-3]]},f,v),(1,0))
        self.assertEqual(query_contact_faces(f,{'planes':[[1,0,0,1],[1,0,0,1]]},f,v),(-1,0))
        self.assertEqual(query_contact_faces(f,{'planes':[[1,0,0,2],[1,0,0,1]]},f,v),(-1,1))

    def test_selector_uses_real_face_queries(self):
        shape={'planes':[[1,0,0,1],[-1,0,0,1]],'vertices':[[-1,0,0],[1,0,0]]}
        moved=self.frame[:3]+[[3,0,0]]
        def no_edge(*args):self.fail('Separated faces must skip edge query')
        result=select_contact_axis(self.frame,shape,moved,shape,edge_enabled=True,
                                   face_query=query_contact_faces,edge_query=no_edge)
        self.assertEqual(result,dict(kind=3,first=0,second=0xffffffff,distance=1))

    def test_empty_planes_and_invalid_empty_support(self):
        value,index=query_contact_faces(self.frame,{'planes':[]},self.frame,{'vertices':[]})
        self.assertLess(value,-1e38);self.assertEqual(index,0xffffffff)
        with self.assertRaises(ValueError):
            query_contact_faces(self.frame,{'planes':[[1,0,0,0]]},self.frame,{'vertices':[]})
