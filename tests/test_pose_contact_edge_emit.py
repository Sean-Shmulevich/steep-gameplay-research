import struct
import unittest
from engine.pose_contact_edge_emit import emit_edge_contact

class EdgeEmitTest(unittest.TestCase):
    def test_closest_endpoints_squared_distance_and_tail(self):
        frame=[[1,0,0],[0,1,0],[0,0,1],[0,0,0]]
        a=dict(vertices=[[1,0,2],[0,0,2]],planes=[[0,1,1,0],[0,-1,1,0]],edges=[(0,1,0,1)])
        b=dict(vertices=[[0,1,0],[0,0,0]],edges=[(0,1,0,0)])
        output=bytearray(b'X'*64)
        self.assertEqual(emit_edge_contact(output,1,frame,a,frame,b,dict(first=0,second=0)),1)
        self.assertEqual(struct.unpack_from('<3f',output),(0,0,1))
        self.assertEqual(struct.unpack_from('<f',output,12),(-4,))
        self.assertEqual(struct.unpack_from('<3f',output,16),(0,0,2))
        self.assertEqual(struct.unpack_from('<3f',output,32),(0,0,0))
        self.assertEqual(struct.unpack_from('<I',output,28),(0,))
        self.assertEqual(struct.unpack_from('<I',output,44),(0xffff0000,))
        self.assertEqual(output[48:],b'X'*16)
    def test_zero_capacity_skips_missing_geometry(self):
        out=bytearray(b'abc')
        self.assertEqual(emit_edge_contact(out,0,None,None,None,None,None),0)
        self.assertEqual(out,b'abc')
