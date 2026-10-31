import struct
import unittest
from engine.pose_body_resource_array import deserialize_pose_body_resource_array
from engine.pose_transform_storage import deserialize_retained_pose_resource_entry


def block(t,p):return struct.pack('<II',0xecd70000|t,len(p)+8)+p


class ResourceArrayTests(unittest.TestCase):
    def fixture(self,data,count=0,capacity=4):
        self.b=bytearray(0x200);struct.pack_into('<QHH',self.b,0xb8,200,count,capacity)
        self.a={200:bytearray([0xa5]*288)};self.r=bytearray(0x50);self.buffers={1000:data};self.events=[]
        struct.pack_into('<QI',self.r,0,1000,len(data));struct.pack_into('<QQ',self.r,0x10,1000,1000)
    def run_reader(self,entry=None,reset=None,grow=None):
        deserialize_pose_body_resource_array(self.b,self.r,body_token=10,buffers=self.buffers,
            entry_arrays=self.a,identity_token=1,read_base=lambda *a:None,
            reset_resource=reset or (lambda *a:self.fail('unexpected reset')),
            grow_entries=grow or (lambda *a:self.fail('unexpected growth')),
            read_entry=entry or (lambda e,r,b,t:self.events.append(t)))

    def test_placeholder_and_actual_entry_composition(self):
        frame=struct.pack('<12f',1,0,0,0,1,0,0,0,1,4,5,6)
        payload=struct.pack('<II',0x73cb9fb7,0xffffeeee)+frame+bytes(36)+bytes(6)
        self.fixture(block(0xe02,struct.pack('<I',2))+block(0xe04,b'')+block(0xe03,payload))
        transforms={2:bytearray(64)}
        def read_entry(e,r,b,t):
            deserialize_retained_pose_resource_entry(e,r,b,entry_token=t,buffers=self.buffers,
                metadata={},object_tables={},fixup_arrays={},grow_fixups=None,identity_token=1,
                transforms=transforms,allocate_transform=lambda:2,release_transform=None)
        self.run_reader(entry=read_entry)
        self.assertEqual(struct.unpack_from('<I',self.b,0x110)[0],1)
        self.assertEqual(struct.unpack_from('<QI',self.a[200],0),(10,0))
        self.assertEqual(struct.unpack_from('<Q',self.a[200],24)[0],1)
        self.assertEqual(struct.unpack_from('<Q',self.a[200],72+24)[0],2)
        self.assertEqual(struct.unpack_from('<3f',transforms[2],48),(4,5,6))
        self.assertEqual(self.r[0x20],0)

    def test_resets_reload_array_and_keep_captured_old_count(self):
        self.fixture(block(0xe02,struct.pack('<I',0)),count=2)
        self.a[300]=bytearray(288)
        struct.pack_into('<Q',self.a[300],72+16,55)
        def reset(b,i,f,z):
            self.events.append(i);struct.pack_into('<Q',b,0xb8,300);struct.pack_into('<H',b,0xc0,0)
            self.assertEqual(z,0)
        self.run_reader(reset=reset)
        self.assertEqual(self.events,[0,1])
        self.assertEqual(struct.unpack_from('<I',self.b,0x110)[0],0)

    def test_unreachable_growth_rejected_and_missing_array_preserved(self):
        self.fixture(block(0xe02,struct.pack('<I',1)),capacity=0)
        with self.assertRaisesRegex(ValueError,'doubling'):self.run_reader()
        self.fixture(b'',count=2)
        before=bytes(self.b);self.run_reader();self.assertEqual(self.b,before)

    def test_entry_attempts_count_even_when_reader_sets_error(self):
        self.fixture(block(0xe02,struct.pack('<I',3)))
        def failed(e,r,b,t):r[0x20]=1
        self.run_reader(entry=failed)
        self.assertEqual(struct.unpack_from('<I',self.b,0x110)[0],3)
        self.assertEqual(self.r[0x20],1)
