import struct
import unittest
from engine.pose_transform_storage import (is_pose_identity_transform, initialize_pose_transform,
    set_pose_transform, deserialize_retained_pose_resource_entry)


def identity():return bytearray(struct.pack('<12f',1,0,0,0,1,0,0,0,1,0,0,0))


class TransformStorageTests(unittest.TestCase):
    def test_threshold_neighbors_and_unordered_comparison(self):
        frame=identity()
        for word,expected in ((0x358637bc,True),(0x358637bd,True),(0x358637be,False),
                              (0x7fc01234,True),(0x7f800000,False),(0x80000000,True)):
            struct.pack_into('<I',frame,36,word)
            self.assertEqual(is_pose_identity_transform(frame),expected)
        frame=identity()
        struct.pack_into('<I',frame,0,0x3f800008)
        self.assertTrue(is_pose_identity_transform(frame))
        struct.pack_into('<I',frame,0,0x3f800009)
        self.assertFalse(is_pose_identity_transform(frame))

    def test_assignment_lifecycle_and_padding(self):
        slot=bytearray(struct.pack('<Q',1));transforms={2:bytearray([0xa5]*64)};events=[]
        def allocate():events.append('allocate');return 2
        def release(token):
            self.assertEqual(struct.unpack('<Q',slot)[0],token);events.append('release')
        services=dict(identity_token=1,transforms=transforms,allocate=allocate,release=release)
        frame=identity();struct.pack_into('<f',frame,36,2.)
        set_pose_transform(slot,frame,**services)
        struct.pack_into('<f',frame,36,3.)
        set_pose_transform(slot,frame,**services)
        self.assertEqual(events,['allocate'])
        self.assertEqual(struct.unpack_from('<f',transforms[2],48)[0],3.)
        for i in range(4):self.assertEqual(transforms[2][16*i+12:16*i+16],b'\xa5'*4)
        set_pose_transform(slot,identity(),**services)
        self.assertEqual(events,['allocate','release']);self.assertEqual(struct.unpack('<Q',slot)[0],1)
        set_pose_transform(slot,identity(),**services)
        self.assertEqual(events,['allocate','release'])

    def test_constructor_ignores_previous_slot(self):
        slot=bytearray(b'\xff'*8)
        initialize_pose_transform(slot,identity(),identity_token=1,transforms={},allocate=lambda:self.fail('allocation'))
        self.assertEqual(struct.unpack('<Q',slot)[0],1)

    def test_resource_entry_loading_allocates_actual_transform(self):
        entry=bytearray(72);struct.pack_into('<Q',entry,24,1)
        frame=identity();struct.pack_into('<f',frame,40,7.)
        payload=struct.pack('<II',0x73cb9fb7,0xffffeeee)+frame+bytes(36)+bytes(6)
        data=struct.pack('<II',0xecd70e03,len(payload)+8)+payload
        reader=bytearray(0x50);struct.pack_into('<QI',reader,0,1000,len(data));struct.pack_into('<QQ',reader,0x10,1000,1000)
        transforms={2:bytearray([0xa5]*64)}
        deserialize_retained_pose_resource_entry(entry,reader,bytearray(0x200),identity_token=1,
            transforms=transforms,allocate_transform=lambda:2,release_transform=lambda t:self.fail('release'),
            entry_token=200,buffers={1000:data},metadata={},object_tables={},fixup_arrays={},grow_fixups=None)
        self.assertEqual(struct.unpack_from('<Q',entry,24)[0],2)
        self.assertEqual(struct.unpack_from('<f',transforms[2],52)[0],7.)
        self.assertEqual(reader[0x20],0)
