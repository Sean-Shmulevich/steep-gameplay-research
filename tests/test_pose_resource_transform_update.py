import struct
import unittest
from engine.pose_resource_transform_update import update_pose_resource_transform,reset_known_pose_resource
from engine.pose_body_resource_array import IDENTITY_XYZ


class ResourceTransformUpdateTests(unittest.TestCase):
    def fixture(self):
        b=bytearray(0x200);struct.pack_into('<Q',b,0xb8,3);struct.pack_into('<Q',b,0x30,4)
        e=bytearray(72);struct.pack_into('<Q',e,16,77);struct.pack_into('<Q',e,24,2);e[68]=1
        return b,e,{3:e},{4:bytearray(0x60)}

    def test_loader_reset_releases_private_transform_not_resource(self):
        b,e,arrays,meta=self.fixture();events=[]
        def release(t):
            self.assertEqual(t,2);self.assertEqual(struct.unpack_from('<Q',e,24)[0],2)
            events.append(t)
        reset_known_pose_resource(b,0,IDENTITY_XYZ,0,entry_arrays=arrays,identity_token=1,
            transforms={2:bytearray(64)},allocate=None,release=release)
        self.assertEqual(events,[2]);self.assertEqual(struct.unpack_from('<Q',e,16)[0],77)
        self.assertEqual(struct.unpack_from('<Q',e,24)[0],1)
        self.assertEqual(b[0xb0],1);self.assertEqual(b[0xaa],0x10)

    def test_immediate_order_reloads_entries_after_bounds_callback(self):
        b,e,arrays,meta=self.fixture();struct.pack_into('<Q',e,24,1);e[68]=0
        replacement=bytearray(e);replacement[68]=1;arrays[5]=replacement;b[0xaa]=0xff
        events=[]
        def bounds(body,zero):
            events.append(('bounds',zero));struct.pack_into('<Q',body,0xb8,5)
        update_pose_resource_transform(b,0,IDENTITY_XYZ,1,entry_arrays=arrays,identity_token=1,
            transforms={},allocate=None,release=None,metadata=meta,refresh_bounds=bounds,
            refresh_first=lambda b:events.append('first'),refresh_second=lambda b:events.append('second'))
        self.assertEqual(events,[('bounds',0),'first','second'])
        self.assertEqual(b[0xb0],0);self.assertEqual(b[0xaa],0xef)

    def test_metadata_gate_defers_derived_work(self):
        b,e,arrays,meta=self.fixture();struct.pack_into('<Q',e,24,1);meta[4][0x52]=8
        update_pose_resource_transform(b,0,IDENTITY_XYZ,1,entry_arrays=arrays,identity_token=1,
            transforms={},allocate=None,release=None,metadata=meta,refresh_bounds=lambda *a:None,
            refresh_first=lambda b:self.fail('gated'),refresh_second=lambda b:self.fail('gated'))
        self.assertEqual(b[0xaa],0x10)

    def test_low_byte_zero_and_entry_gate_preserve_other_flags(self):
        b,e,arrays,meta=self.fixture();struct.pack_into('<Q',e,24,1);e[68]=0;b[0xaa]=0xa5
        reset_known_pose_resource(b,0,IDENTITY_XYZ,256,entry_arrays=arrays,identity_token=1,
            transforms={},allocate=None,release=None)
        self.assertEqual(b[0xaa],0xa5);self.assertEqual(b[0xb0],1)
