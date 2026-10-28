import struct
import unittest
from engine.pose_grid_box_contact import emit_grid_box_contacts, emit_box_grid_contacts


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


class BoxGridAdapterTest(unittest.TestCase):
    def invoke(self, output, capacity, preliminary=True, mask=0):
        resource=bytearray(0xc0)
        struct.pack_into('<I',resource,0x40,2)
        struct.pack_into('<2H',resource,0x68,3,3)
        struct.pack_into('<2f',resource,0x70,1,1)
        struct.pack_into('<3f',resource,0x7c,0,0,-1)
        struct.pack_into('<3f',resource,0x88,2,2,1)
        struct.pack_into('<2H',resource,0x9c,2,2)
        frame=GridBoxContactTest.frame
        return emit_box_grid_contacts(output,capacity,resource,[0]*9,
            [*frame[:3],[.75,.75,-.1]],frame,[.25]*3,
            dict(default20='p',mapb0=None,tablea0=[]),dict(default20='p'),
            profiles={'p':dict(mask48=mask,mask50=mask)},preliminary=preliminary)

    def test_zero_capacity_success_reverses_existing_record(self):
        original=struct.pack('<12I',*range(12))+b'tail'
        output=bytearray(original)
        self.assertEqual(self.invoke(output,0),1)
        expected=list(range(12))
        expected[:3]=[word ^ 0x80000000 for word in range(3)]
        expected[4:7]=[8,9,10]
        expected[8:11]=[4,5,6]
        self.assertEqual(output,struct.pack('<12I',*expected)+b'tail')

    def test_preliminary_points_and_normal_have_box_first_roles(self):
        output=bytearray(48)+b'tail'
        self.assertEqual(self.invoke(output,1),1)
        self.assertEqual(struct.unpack_from('<3f',output),(-0.,-0.,-1.))
        self.assertEqual(struct.unpack_from('<2f',output,16),(.75,.75))
        self.assertAlmostEqual(struct.unpack_from('<f',output,24)[0],-.1)
        self.assertAlmostEqual(struct.unpack_from('<f',output,40)[0],.25)
        self.assertEqual(output[48:],b'tail')

    def test_no_contacts_preserves_backing_record(self):
        output=bytearray(range(48))
        self.assertEqual(self.invoke(output,0,preliminary=False),0)
        self.assertEqual(output,bytearray(range(48)))

    def test_missing_backing_record_is_rejected_before_mutation(self):
        output=bytearray(47)
        with self.assertRaises(ValueError):
            self.invoke(output,0)
        self.assertEqual(output,bytearray(47))
