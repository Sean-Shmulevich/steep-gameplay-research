import struct
import unittest
from engine.pose_body_destruction import destroy_known_pose_body
from engine.pose_resource_array_clear import clear_pose_body_resources


class BodyDestructionTests(unittest.TestCase):
    def test_joined_resource_cleanup_precedes_array_and_metadata_release(self):
        body=bytearray(0x200);struct.pack_into('<Q',body,0x30,50)
        struct.pack_into('<QHH',body,0xb8,200,1,4);struct.pack_into('<I',body,0x110,1)
        struct.pack_into('<QQ',body,0x1b8,10,20)
        entry=bytearray(72);struct.pack_into('<QQ',entry,16,30,40);resources={30:bytearray(32)}
        events=[]
        def clear(b):
            clear_pose_body_resources(b,body_token=100,entry_arrays={200:entry},resources=resources,
                identity_token=1,notify=lambda *a:events.append('resource notification'),
                destroy=lambda *a:events.append('resource destruction'),release_transform=lambda *a:events.append('transform release'))
        def parameter(kind,token):
            events.append(kind);self.assertEqual(struct.unpack_from('<Q',body,0)[0],2)
        def notify(b,event):
            self.assertEqual(event,10);self.assertEqual(struct.unpack_from('<Q',b,0xb8)[0],0)
            self.assertEqual(struct.unpack_from('<H',b,0xc2)[0],0)
            events.append('body notification');struct.pack_into('<Q',b,0x30,60)
        def metadata(token):self.assertEqual(token,60);events.append('metadata release')
        destroy_known_pose_body(body,body_token=100,physical_table=2,resource_body_table=3,base_table=4,final_table=5,
            entry_arrays={200:entry},release_parameter=parameter,clear_resources=clear,
            release_entries=lambda *a:events.append('array release'),notify_body=notify,release_metadata=metadata)
        self.assertEqual(events,['scalar_vector','triple','resource notification','resource destruction',
            'transform release','array release','body notification','metadata release'])
        self.assertEqual(struct.unpack_from('<Q',body,0)[0],5)
        self.assertEqual(struct.unpack_from('<QQ',body,0x1b8),(0,0))
        self.assertEqual(struct.unpack_from('<Q',body,0x30)[0],60)
        self.assertEqual(struct.unpack_from('<QQ',entry,16),(0,1))

    def test_zero_capacity_skips_external_free_but_descriptor_is_cleared(self):
        body=bytearray(0x200);struct.pack_into('<Q',body,0xb8,200)
        destroy_known_pose_body(body,body_token=100,physical_table=2,resource_body_table=3,base_table=4,final_table=5,
            entry_arrays={},release_parameter=None,clear_resources=lambda b:None,
            release_entries=lambda *a:self.fail('free'),notify_body=lambda *a:None,release_metadata=lambda *a:None)
        self.assertEqual(struct.unpack_from('<Q',body,0xb8)[0],0)
