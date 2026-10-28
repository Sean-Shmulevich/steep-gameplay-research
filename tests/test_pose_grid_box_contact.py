import struct
import unittest
from engine.pose_grid_box_contact import emit_grid_box_contacts


class GridBoxContactTest(unittest.TestCase):
    frame=[[1,0,0],[0,1,0],[0,0,1],[0,0,0]]
    def run_case(self,capacity,preliminary,mask=1):
        r=bytearray(0xc0)
        struct.pack_into('<I',r,0x40,2);struct.pack_into('<2H',r,0x68,3,3)
        struct.pack_into('<2f',r,0x70,1,1);struct.pack_into('<3f',r,0x7c,0,0,-1)
        struct.pack_into('<3f',r,0x88,2,2,1);struct.pack_into('<2H',r,0x9c,2,2)
        output=bytearray(b'X'*(capacity*48+16))
        count=emit_grid_box_contacts(output,capacity,r,[0]*9,self.frame,
            [*self.frame[:3],[.75,.75,-.1]],[.25,.25,.25],
            dict(default20='p',mapb0=None,tablea0=[]),dict(default20='p'),
            profiles={'p':dict(mask48=mask,mask50=mask)},preliminary=preliminary)
        return count,output

    def test_preliminary_can_return_one_without_record_and_before_profile_gate(self):
        count,out=self.run_case(0,True,0)
        self.assertEqual(count,1);self.assertEqual(out,b'X'*16)
        count,out=self.run_case(1,True,0)
        self.assertEqual(count,1);self.assertEqual(out[48:],b'X'*16)
        self.assertLess(struct.unpack_from('<f',out,12)[0],0)

    def test_rejected_profile_preserves_records_on_triangle_path(self):
        count,out=self.run_case(4,False,0)
        self.assertEqual(count,0);self.assertEqual(out,b'X'*208)
