import struct
import unittest
from engine.pose_body_load import finalize_pose_body_resources,load_pose_body_object
from engine.pose_body_bounds import refresh_pose_body_bounds


class BodyLoadTests(unittest.TestCase):
    def test_duplicate_resources_and_null_entries(self):
        body=bytearray(0x200);entries=bytearray(216);resource=bytearray([0xa5]*0x60)
        struct.pack_into('<Q',body,0xb8,1);struct.pack_into('<H',body,0xc0,3)
        struct.pack_into('<QI',entries,0,10,11);struct.pack_into('<Q',entries,16,2)
        struct.pack_into('<QI',entries,144,20,21);struct.pack_into('<Q',entries,160,2)
        finalize_pose_body_resources(body,entry_arrays={1:entries},resources={2:resource})
        self.assertEqual(struct.unpack_from('<QI',resource,0x30),(20,21))
        self.assertEqual(resource[:0x30],bytes([0xa5]*0x30));self.assertEqual(resource[0x3c:],bytes([0xa5]*0x24))

    def fixture(self,payload=b'\4\0\0\0'):
        data=struct.pack('<II',0xecd70c01,len(payload)+8)+payload
        reader=bytearray(0x50);struct.pack_into('<QI',reader,0,1000,len(data));struct.pack_into('<QQ',reader,0x10,1000,1000)
        provider=bytearray(0x610);struct.pack_into('<Q',provider,0x608,123)
        return provider,reader,{1000:data}

    def test_load_finalizes_before_bounds_service_uses_backlinks(self):
        p,r,buffers=self.fixture();events=[];body=bytearray(0x200);entries=bytearray(72);resource=bytearray(0x60);meta=bytearray(0x60)
        frame=bytearray(64)
        for i in range(3):struct.pack_into('<f',frame,i*16+i*4,1.)
        def create(factory,kind):events.append(('create',factory,kind));return 7
        def decode(t,reader):
            events.append(('decode',t));body[0x40:0x80]=frame
            struct.pack_into('<Q',body,0x30,4);struct.pack_into('<Q',body,0xb8,1);struct.pack_into('<H',body,0xc0,1)
            struct.pack_into('<QI',entries,0,7,9);struct.pack_into('<QQ',entries,16,2,3)
        def finalize(t):
            events.append(('finalize',t));finalize_pose_body_resources(body,entry_arrays={1:entries},resources={2:resource})
        self.assertEqual(load_pose_body_object(p,r,buffers=buffers,create=create,deserialize=decode,finalize=finalize),7)
        def bounds(t,transform):
            self.assertEqual(struct.unpack_from('<QI',resource,0x30),(7,9));return [0.,0.,0.,1.,2.,3.]
        refresh_pose_body_bounds(body,entry_arrays={1:entries},transforms={3:frame},metadata={4:meta},resource_bounds=bounds)
        self.assertEqual(events,[('create',123,4),('decode',7),('finalize',7)])
        self.assertEqual(struct.unpack_from('<6f',meta,4),(0,0,0,1,2,3))

    def test_minimum_four_bytes_null_factory_and_missing_block(self):
        p,r,buffers=self.fixture(b'\4\0')
        self.assertEqual(load_pose_body_object(p,r,buffers=buffers,create=lambda *a:self.fail('short'),deserialize=None,finalize=None),0)
        self.assertEqual(r[0x20],1)
        p,r,buffers=self.fixture()
        self.assertEqual(load_pose_body_object(p,r,buffers=buffers,create=lambda *a:0,deserialize=lambda *a:self.fail('null'),finalize=lambda *a:self.fail('null')),0)
        self.assertEqual(struct.unpack_from('<Q',r,0x10)[0],1010)


if __name__=='__main__':unittest.main()
