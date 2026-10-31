import struct
import unittest
from engine.pose_body_parameters import (set_pose_body_scalar, set_pose_body_vector,
    set_pose_body_parameter, deserialize_retained_physical_pose_body)


def f(*values): return struct.pack('<'+'f'*len(values), *values)


class BodyParameterTests(unittest.TestCase):
    def setUp(self):
        self.body=bytearray(0x200);self.records={};self.events=[]
        def allocate(kind):
            token=len(self.records)+1;self.records[token]=bytearray([0xa5]*16)
            self.events.append(('allocate',kind,token));return token
        def release(token):
            self.assertIn(token,struct.unpack_from('<QQ',self.body,0x1b8))
            self.events.append(('release',token))
        self.services=dict(records=self.records,allocate=allocate,release=release)

    def test_scalar_vector_share_storage_and_release_only_when_both_default(self):
        set_pose_body_scalar(self.body,f(3),**self.services)
        self.assertEqual(self.records[1],f(0,0,0,3))
        set_pose_body_vector(self.body,f(1,2,3),**self.services)
        set_pose_body_scalar(self.body,f(-0.),**self.services)
        self.assertEqual(self.records[1],f(1,2,3,-0.))
        self.assertEqual(len(self.events),1)
        set_pose_body_vector(self.body,f(0,0,0),**self.services)
        self.assertEqual(struct.unpack_from('<Q',self.body,0x1b8)[0],0)
        self.assertEqual(self.events[-1],('release',1))

    def test_triple_defaults_nan_branch_and_padding(self):
        set_pose_body_parameter(self.body,1,f(2),**self.services)
        self.assertEqual(self.records[1][:12],f(-1,2,-1))
        self.assertEqual(self.records[1][12:],b'\xa5'*4)
        set_pose_body_parameter(self.body,1,struct.pack('<I',0x7fc12345),**self.services)
        self.assertEqual(struct.unpack_from('<Q',self.body,0x1c0)[0],0)
        self.assertEqual(self.events[-1],('release',1))
        self.assertEqual(self.records[1][4:8],struct.pack('<I',0x7fc12345))
        set_pose_body_parameter(self.body,0,f(-1),**self.services)
        self.assertEqual(len(self.events),2)

    def test_nan_and_signed_zero_do_not_allocate_default_record(self):
        set_pose_body_scalar(self.body,struct.pack('<I',0x7fc12345),**self.services)
        set_pose_body_vector(self.body,f(-0.,0.,float('nan')),**self.services)
        self.assertEqual(self.events,[])

    def test_deserialization_composes_five_setters_and_preserves_motion(self):
        def block(tag,data):return struct.pack('<II',0xecd70000|tag,len(data)+8)+data
        data=block(0x1001,bytes(92))+block(0x1002,f(1,2,3,4,5,6))
        data+=block(0x1003,f(2,3,4,5))+block(0x1004,f(-1,7,-1))
        reader=bytearray(0x50);struct.pack_into('<QI',reader,0,1000,len(data))
        struct.pack_into('<QQ',reader,0x10,1000,1000)
        deserialize_retained_physical_pose_body(self.body,reader,buffers={1000:data},
            read_base=lambda *args:None,**self.services)
        self.assertEqual(self.records[1],f(3,4,5,2))
        self.assertEqual(self.records[2][:12],f(-1,7,-1))
        self.assertEqual(self.body[0x1a0:0x1b8],f(1,2,3,4,5,6))
        self.assertEqual(reader[0x20],0)
