import struct
import unittest
from engine.pose_resource_array_storage import resize_pose_resource_array
from engine.pose_body_resource_array import deserialize_pose_body_resource_array


class ResourceArrayStorageTests(unittest.TestCase):
    def test_inline_growth_preserves_only_live_entry_and_allocator_arguments(self):
        body=bytearray([0xa5]*0x200);struct.pack_into('<QHH',body,0xb8,1000+0xc8,1,1)
        arrays={2000:bytearray([0xcc]*288)};events=[]
        def allocate(*args):events.append(args);return 2000
        resize_pose_resource_array(body,4,body_token=1000,entry_arrays=arrays,allocate=allocate,reallocate=None,release=None)
        self.assertEqual(events,[(288,16,0x4c)])
        self.assertEqual(arrays[2000][:72],b'\xa5'*72);self.assertEqual(arrays[2000][72:],b'\xcc'*216)
        self.assertEqual(struct.unpack_from('<QHH',body,0xb8),(2000,1,4))

    def test_shrink_copies_before_release_and_zero_keeps_stale_inline(self):
        for requested in (0,1):
            body=bytearray([0xa5]*0x200);struct.pack_into('<QHH',body,0xb8,2000,3,4)
            arrays={2000:bytearray([0xcc]*288)};events=[]
            def release(token):
                events.append(token)
                self.assertEqual(struct.unpack_from('<Q',body,0xb8)[0],2000)
                self.assertEqual(body[0xc8:0x110],bytes([0xcc if requested else 0xa5])*72)
            resize_pose_resource_array(body,requested,body_token=1000,entry_arrays=arrays,allocate=None,reallocate=None,release=release)
            self.assertEqual(events,[2000]);self.assertEqual(struct.unpack_from('<QHH',body,0xb8),(1200,requested,1))
            arrays[1200][0]=7;self.assertEqual(body[0xc8],7)

    def test_equal_capacity_is_noop_even_for_inconsistent_count(self):
        body=bytearray(0x200);struct.pack_into('<QHH',body,0xb8,1200,2,1)
        before=bytes(body)
        resize_pose_resource_array(body,1,body_token=1000,entry_arrays={},allocate=None,reallocate=None,release=None)
        self.assertEqual(body,before)

    def test_array_reader_grows_from_inline_and_initializes_new_entries(self):
        def block(t,p):return struct.pack('<II',0xecd70000|t,len(p)+8)+p
        data=block(0xe02,struct.pack('<I',2))+block(0xe04,b'')*2
        body=bytearray(0x200);struct.pack_into('<QHH',body,0xb8,1200,0,1)
        arrays={1200:memoryview(body)[0xc8:0x110]};reader=bytearray(0x50)
        struct.pack_into('<QI',reader,0,3000,len(data));struct.pack_into('<QQ',reader,0x10,3000,3000)
        def allocate(size,alignment,tag):arrays[2000]=bytearray(size);return 2000
        def grow(b,n):resize_pose_resource_array(b,n,body_token=1000,entry_arrays=arrays,allocate=allocate,reallocate=None,release=None)
        deserialize_pose_body_resource_array(body,reader,body_token=1000,buffers={3000:data},entry_arrays=arrays,
            identity_token=1,read_base=lambda *a:None,reset_resource=None,grow_entries=grow,read_entry=None)
        self.assertEqual(struct.unpack_from('<QHH',body,0xb8),(2000,2,2))
        self.assertEqual(struct.unpack_from('<QI',arrays[2000],72),(1000,1))
        self.assertEqual(struct.unpack_from('<Q',arrays[2000],72+24)[0],1)
