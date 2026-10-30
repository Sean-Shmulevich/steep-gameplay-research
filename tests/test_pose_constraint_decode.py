import struct
import unittest
from engine.pose_constraint_decode import deserialize_pose_command_record
from engine.pose_reference_reader import replay_pose_references


def block(tag,data):return struct.pack('<II',0xecd70000|tag,len(data)+8)+data
def ref(kind,index):return struct.pack('<II',0x73cb0000|kind,index)


class ConstraintDecodeTests(unittest.TestCase):
    def fixture(self,data,capacity=8):
        self.r=bytearray([0xa5]*0x200);struct.pack_into('<QQ',self.r,8,1,2);struct.pack_into('<I',self.r,0x74,0)
        self.reader=bytearray(0x50);struct.pack_into('<QI',self.reader,0,1000,len(data));struct.pack_into('<QQ',self.reader,0x10,1000,1000)
        struct.pack_into('<QII',self.reader,0x28,2000,2,capacity);struct.pack_into('<QII',self.reader,0x38,3000,0,8)
        self.tables={2000:bytearray([0x55]*(16*capacity))};self.fixups={3000:bytearray(8*24)}
        for i in range(2):struct.pack_into('<QI',self.tables[2000],16*i,i+1,0x9fb6)
        self.bodies={i:bytearray(0x40) for i in (1,2)};self.metadata={i:bytearray(0x60) for i in (11,12)}
        for i in (1,2):struct.pack_into('<Q',self.bodies[i],0x30,i+10);struct.pack_into('<I',self.metadata[i+10],0x54,i*10)
        self.kw=dict(constraint_token=5000,buffers={1000:data},object_tables=self.tables,fixup_arrays=self.fixups,
            grow_objects=self.grow,grow_fixups=lambda *a:self.fail('fixup capacity'),bodies=self.bodies,metadata=self.metadata)
    def grow(self,reader,cap):
        old,count=struct.unpack_from('<QI',reader,0x28);self.tables[2001]=self.tables[old][:count*16]+bytearray([0x77]*((cap-count)*16))
        struct.pack_into('<QII',reader,0x28,2001,count,cap)

    def test_self_reference_endpoint_override_and_forward_replay(self):
        data=(block(0x301,struct.pack('<Q',123))+
            block(0x2602,ref(0x9fb6,0)+b'\1'+ref(0x9fb6,1))+
            block(0x2c02,ref(0x9fb6,1)+ref(0x9fb6,0))+
            block(0x2c03,ref(0x9fb9,2)*4)+
            block(0x2609,ref(0x9fba,3)+struct.pack('<IB',17,255))+
            block(0x2607,struct.pack('<IB',1,1))+block(0x2608,bytes(range(64))))
        self.fixture(data,2);callback=bytes(self.r[0x1f8:]);deserialize_pose_command_record(self.r,self.reader,**self.kw)
        self.assertEqual(struct.unpack_from('<QQII',self.r,8),(2,1,20,10))
        self.assertEqual(struct.unpack_from('<4Q',self.r,0x20),(5000,)*4)
        self.assertEqual(struct.unpack_from('<Q',self.r,0x50)[0],123);self.assertEqual(self.r[0x59],1)
        self.assertEqual(self.r[0x78:0xb8],bytes(range(64)));self.assertEqual(self.r[0x1f8:],callback)
        self.assertEqual(struct.unpack_from('<QI',self.tables[2001],32),(5000,0x9fb9))
        self.assertEqual(self.tables[2001][44:48],bytes([0x77]*4))
        self.assertEqual(struct.unpack_from('<QII',self.fixups[3000],0),(5000+0x60,3,0x9fba))
        struct.pack_into('<QI',self.tables[2001],48,999,0x9fba);struct.pack_into('<I',self.reader,0x30,4)
        self.assertTrue(replay_pose_references(self.reader,object_tables=self.tables,fixup_arrays=self.fixups,
            destinations={5000+0x60:memoryview(self.r)[0x60:0x68]},allocate_scratch=bytearray,
            release_scratch=lambda s:None,grow_fixups=lambda *a:self.fail('capacity'),retain=lambda t:self.fail('ordinary')))
        self.assertEqual(struct.unpack_from('<Q',self.r,0x60)[0],999)

    def test_absent_userdata_zeroes_but_other_missing_fields_remain(self):
        data=block(0x2607,struct.pack('<IB',0,0));self.fixture(data);before=bytes(self.r)
        deserialize_pose_command_record(self.r,self.reader,**self.kw)
        self.assertEqual(self.r[0x50:0x58],bytes(8));self.assertEqual(self.r[8:0x40],before[8:0x40])
        self.assertEqual(self.r[0x60:0x70],before[0x60:0x70]);self.assertEqual(self.reader[0x20],0)

    def test_reference_type_failure_sets_error_but_loading_continues(self):
        # Matching wire type, wrong table type consumes both reference words.
        data=block(0x2602,ref(0x9fb6,0)+b'\0')+block(0x2607,struct.pack('<IB',0,1))
        self.fixture(data);struct.pack_into('<I',self.tables[2000],8,0x9999)
        deserialize_pose_command_record(self.r,self.reader,**self.kw)
        self.assertEqual(self.reader[0x20],1);self.assertEqual(struct.unpack_from('<QQ',self.r,8),(1,0))
        self.assertEqual(self.r[0x70],1)


if __name__=='__main__':unittest.main()
