import struct
import unittest
from engine.pose_body_base_decode import deserialize_pose_body_base
from engine.pose_reference_reader import replay_pose_references


def block(tag,data):return struct.pack('<II',0xecd70000|tag,len(data)+8)+data

def ref(kind,index):return struct.pack('<II',0x73cb0000|kind,index)


class BaseBodyDecodeTests(unittest.TestCase):
    def fixture(self,data,capacity=8):
        self.body=bytearray([0xa5]*0x200);struct.pack_into('<Q',self.body,0x30,2)
        self.meta=bytearray([0xa5]*0x60);self.reader=bytearray(0x50)
        self.tables={3:bytearray([0xcc]*128)};self.fixups={4:bytearray([0xdd]*192)}
        struct.pack_into('<QI',self.reader,0,1000,len(data))
        struct.pack_into('<QQ',self.reader,0x10,1000,1000)
        struct.pack_into('<QII',self.reader,0x28,3,0,capacity)
        struct.pack_into('<QII',self.reader,0x38,4,0,8)
        self.kwargs=dict(body_token=100,buffers={1000:data},metadata={2:self.meta},object_tables=self.tables,
            fixup_arrays=self.fixups,grow_objects=self.grow,grow_fixups=lambda *a:self.fail('unexpected fixup growth'))

    def grow(self,reader,capacity):
        self.tables[5]=bytearray([0xee]*(capacity*16))
        struct.pack_into('<Q',reader,0x28,5);struct.pack_into('<I',reader,0x34,capacity)

    def decode(self):deserialize_pose_body_base(self.body,self.reader,**self.kwargs)

    def required(self,flags=b'\x82'):
        return block(0xc02,b'\x34\x12')+block(0xc05,bytes(range(58)))+block(0xc06,flags)

    def test_metadata_preserves_key_owner_and_priority_and_transform_padding(self):
        self.fixture(self.required()+block(0xc0b,bytes(range(48))))
        self.decode()
        self.assertEqual(self.meta[4:0x1c],bytes(range(24)))
        self.assertEqual(self.meta[0x30:0x50],bytes(range(24,56)))
        self.assertEqual(self.meta[0x53],0xa8);self.assertEqual(self.meta[0x52],57)
        for a,b in ((0x20,0x30),(0x50,0x52),(0x54,0x58)):
            self.assertEqual(self.meta[a:b],b'\xa5'*(b-a))
        self.assertEqual(self.body[0x1c:0x20],b'\x34\x12\0\0')
        for i in range(4):
            start=0x40+16*i
            self.assertEqual(self.body[start:start+12],bytes(range(12*i,12*i+12)))
            self.assertEqual(self.body[start+12:start+16],b'\xa5'*4)

    def test_legacy_flag_extension_and_absent_defaults(self):
        for tail in (b'',b'\x44',b'\x44\x55'):
            self.fixture(self.required(b'\x82'+tail));self.decode()
            self.assertEqual(self.body[0xaa],0x82)
            self.assertEqual(self.body[0xa8:0xaa],tail if len(tail)==2 else bytes(2))
            self.assertEqual(self.body[0x10:0x18],bytes(8))
            self.assertEqual(self.body[0x20:0x28],bytes(8))
            self.assertEqual(self.body[0x80:0x88],b'\xa5'*8)
            self.assertEqual(self.body[0x90:0x98],b'\xa5'*8)

    def test_registration_grows_before_loading_even_when_required_blocks_missing(self):
        self.fixture(b'',capacity=0);self.decode()
        self.assertEqual(struct.unpack_from('<QI',self.tables[5],0),(100,0x9fb6))
        self.assertEqual(self.tables[5][12:16],b'\xee'*4)
        self.assertEqual(struct.unpack_from('<I',self.reader,0x30)[0],1)
        self.assertEqual(self.reader[0x20],1)
        self.assertEqual(self.body[0x1c:0x20],bytes(4))

    def test_forward_ring_head_resolves_after_constraint_registration(self):
        self.fixture(self.required()+block(0xc0a,ref(0x9fb9,1)))
        self.decode()
        self.assertEqual(struct.unpack_from('<I',self.reader,0x40)[0],1)
        self.assertEqual(self.body[0x90:0x98],b'\xa5'*8)
        struct.pack_into('<QI',self.tables[3],16,700,0x9fb9)
        struct.pack_into('<I',self.reader,0x30,2)
        self.assertTrue(replay_pose_references(self.reader,object_tables=self.tables,fixup_arrays=self.fixups,
            destinations={100+0x90:memoryview(self.body)[0x90:0x98]},allocate_scratch=bytearray,
            release_scratch=lambda *a:None,grow_fixups=lambda *a:self.fail('growth'),retain=lambda *a:self.fail('retain')))
        self.assertEqual(struct.unpack_from('<Q',self.body,0x90)[0],700)
        self.assertEqual(struct.unpack_from('<I',self.reader,0x40)[0],0)
