import unittest
from engine.pose_contact_edge_query import query_contact_edges

class EdgeQueryTest(unittest.TestCase):
    frame=[[1,0,0],[0,1,0],[0,0,1],[0,0,0]]
    def shapes(self):
        a=dict(vertices=[[1,0,1],[0,0,1]],planes=[[0,1,1,0],[0,-1,1,0]],edges=[(0,1,0,1)])
        b=dict(vertices=[[0,1,0],[0,0,0]],planes=[[-1,0,1,0],[1,0,1,0]],edges=[(0,1,0,1)])
        return a,b
    def test_selected_negative_separation_and_first_tie(self):
        a,b=self.shapes();a['edges']*=2;b['edges']*=2;result={}
        query_contact_edges(self.frame,a,self.frame,b,result)
        self.assertEqual(result,dict(distance=-1,first=0,second=0))
    def test_zero_separation_and_empty_edges_reset_seed(self):
        a,b=self.shapes();a['vertices']=[[1,0,0],[0,0,0]];result=dict(distance=5,first=3,second=4)
        query_contact_edges(self.frame,a,self.frame,b,result)
        self.assertEqual(result['first'],0xffffffff)
        a['edges']=[];result['first']=42
        query_contact_edges(self.frame,a,self.frame,b,result)
        self.assertEqual(result['first'],0xffffffff);self.assertLess(result['distance'],-1e38)
