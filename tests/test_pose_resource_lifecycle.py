import struct
import unittest
from engine.pose_resource_lifecycle import dispatch_pose_resource_event,destroy_pose_box_resource
from engine.pose_resource_array_clear import clear_pose_body_resources


class ResourceLifecycleTests(unittest.TestCase):
    def test_notification_copy_and_captured_callback(self):
        manager=bytearray(0x40);struct.pack_into('<Q',manager,0x20,7)
        descriptor=bytearray(range(16));events=[]
        def invoke(fn,copy,event,key):
            events.append((fn,bytes(copy),event,key));copy[:]=b'\xff'*16
            struct.pack_into('<Q',manager,0x20,0)
        dispatch_pose_resource_event(manager,descriptor,0x100000001,9,invoke=invoke)
        dispatch_pose_resource_event(manager,b'',1,9,invoke=invoke)
        self.assertEqual(events,[(7,bytes(range(16)),1,9)])
        self.assertEqual(descriptor,bytearray(range(16)))

    def test_box_child_and_pool_order_all_flags(self):
        for flags in range(8):
            resource=bytearray(0x50);struct.pack_into('<Q',resource,0x20,12);events=[]
            def child(t):
                events.append('child');self.assertEqual(struct.unpack_from('<Q',resource,0)[0],2)
                self.assertEqual(struct.unpack_from('<Q',resource,0x20)[0],12)
            def storage(t):
                events.append('storage');self.assertEqual(struct.unpack_from('<Q',resource,0)[0],3)
                self.assertEqual(struct.unpack_from('<Q',resource,0x20)[0],0)
            destroy_pose_box_resource(10,flags,resources={10:resource},destruction_table=2,base_table=3,
                release_child=child,release_storage=storage)
            self.assertEqual(events,['child']+(['storage'] if flags&1 and not flags&4 else []))

    def test_clear_composes_notification_box_destructor_and_transform_release(self):
        body=bytearray(0x200);struct.pack_into('<QHH',body,0xb8,1,1,1);struct.pack_into('<I',body,0x110,1)
        entry=bytearray(72);struct.pack_into('<QQ',entry,16,10,20)
        resource=bytearray(0x50);struct.pack_into('<Q',resource,0x10,77);struct.pack_into('<Q',resource,0x20,12)
        manager=bytearray(0x40);struct.pack_into('<Q',manager,0x20,7);events=[]
        def notify(owner,index,key,event):
            # Zero descriptor padding is authored for this fixture only.
            descriptor=struct.pack('<QII',owner,index,0)
            dispatch_pose_resource_event(manager,descriptor,event,key,
                invoke=lambda fn,d,e,k:events.append(('notify',struct.unpack('<QII',d)[:2],e,k)))
        def destroy(t,flags):
            destroy_pose_box_resource(t,flags,resources={10:resource},destruction_table=2,base_table=3,
                release_child=lambda t:events.append(('child',t)),release_storage=lambda t:events.append(('storage',t)))
        clear_pose_body_resources(body,body_token=100,entry_arrays={1:entry},resources={10:resource},identity_token=99,
            notify=notify,destroy=destroy,release_transform=lambda t:events.append(('transform',t)))
        self.assertEqual(events,[('notify',(100,0),1,77),('child',12),('storage',10),('transform',20)])
        self.assertEqual(struct.unpack_from('<QQ',entry,16),(0,99))
