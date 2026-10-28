import unittest
from engine.pose_contact_axis_selection import select_contact_axis, select_geometry_contact_axis
from reference.central_impulse import f32

class AxisSelectionTest(unittest.TestCase):
    def run_case(self,values,edge_value,enabled=True):
        calls=[]
        def face(*args):
            n=len(calls);calls.append(args);return values[n],10+n
        def edge(*args):
            calls.append(args[:-1]);args[-1].update(distance=edge_value,first=20,second=21)
        result=select_contact_axis('a','A','b','B',edge_enabled=enabled,face_query=face,edge_query=edge)
        return result,calls

    def test_separation_short_circuits_and_reverses_second_query(self):
        result,calls=self.run_case([1,2],3)
        self.assertEqual(result['kind'],3);self.assertEqual(len(calls),1)
        result,calls=self.run_case([-1,1],3)
        self.assertEqual(result['kind'],3);self.assertEqual(result['first'],0xffffffff)
        self.assertEqual(calls[1],('b','B','a','A'))

    def test_bias_equality_does_not_select_edge(self):
        boundary=f32(f32(f32(-1)*f32(.98))+f32(.01))
        result,_=self.run_case([-1,-1],boundary)
        self.assertEqual(result['kind'],1)
        result,_=self.run_case([-1,-1],0)
        self.assertEqual(result['kind'],2)
        result,calls=self.run_case([-1,-1],0,False)
        self.assertEqual(result['kind'],1);self.assertEqual(len(calls),2)

    def test_connected_geometry_separation_and_overlap(self):
        frame=[[1,0,0],[0,1,0],[0,0,1],[0,0,0]]
        shape={'planes':[[1,0,0,1],[-1,0,0,1]],
               'vertices':[[-1,0,0],[1,0,0]],'edges':[]}
        separated=frame[:3]+[[3,0,0]]
        self.assertEqual(select_geometry_contact_axis(frame,shape,separated,shape),
                         dict(kind=3,first=0,second=0xffffffff,distance=1))
        self.assertEqual(select_geometry_contact_axis(frame,shape,frame,shape),
                         dict(kind=1,first=0xffffffff,second=0,distance=-2))
