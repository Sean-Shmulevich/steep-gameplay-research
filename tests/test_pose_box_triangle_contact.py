import struct
import unittest
from engine.pose_box_triangle_contact import emit_box_triangle_contacts


class BoxTriangleTest(unittest.TestCase):
    frame = [[1,0,0],[0,1,0],[0,0,1],[0,0,0]]
    triangle = [[-3,-3,0],[3,-3,0],[0,3,0]]

    def test_crossing_plane_generates_contacts_and_capacity_prefix(self):
        output = bytearray(b'X'*400)
        n = emit_box_triangle_contacts(output,8,[1,1,1],self.frame,self.triangle)
        self.assertEqual(n,4)
        for i in range(n):
            self.assertEqual(struct.unpack_from('<4f',output,i*48),(0,0,-1,-1))
            self.assertEqual(struct.unpack_from('<I',output,i*48+28),(0,))
            self.assertEqual(struct.unpack_from('<I',output,i*48+44),(0xffff0000,))
        self.assertEqual(output[n*48:],b'X'*(400-n*48))
        limited = bytearray(b'Y'*64)
        self.assertEqual(emit_box_triangle_contacts(limited,1,[1,1,1],self.frame,self.triangle),1)
        self.assertEqual(limited[:48],output[:48])
        self.assertEqual(limited[48:],b'Y'*16)

    def test_separation_and_zero_capacity_preserve_output(self):
        for z,capacity in [(4,8),(0,0)]:
            output = bytearray(b'X'*384)
            triangle = [[x,y,z] for x,y,_ in self.triangle]
            self.assertEqual(emit_box_triangle_contacts(output,capacity,[1,1,1],self.frame,triangle),0)
            self.assertEqual(output,b'X'*384)
