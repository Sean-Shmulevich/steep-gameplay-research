import struct
import unittest
from engine.pose_resource_array_clear import clear_pose_body_resources


class ResourceArrayClearTests(unittest.TestCase):
    def fixture(self):
        self.body=bytearray(0x200);struct.pack_into('<QHH',self.body,0xb8,1,3,4)
        self.entries=bytearray(216);self.arrays={1:self.entries};self.resources={10:bytearray(32),20:bytearray(32)}
        for i,(resource,transform) in enumerate(((10,100),(0,200),(20,300))):
            struct.pack_into('<QQ',self.entries,72*i+16,resource,transform)
        self.events=[]
    def run_clear(self,notify=None,destroy=None,release=None):
        clear_pose_body_resources(self.body,body_token=7,entry_arrays=self.arrays,resources=self.resources,identity_token=99,
            notify=notify or (lambda *a:self.events.append(('notify',a[1]))),
            destroy=destroy or (lambda *a:self.events.append(('destroy',a[0]))),
            release_transform=release or (lambda t:self.events.append(('transform',t))))

    def test_reverse_order_null_skip_and_counter_wrap(self):
        self.fixture();self.run_clear()
        self.assertEqual(self.events,[('notify',2),('destroy',20),('transform',300),('notify',0),('destroy',10),('transform',100)])
        self.assertEqual(struct.unpack_from('<I',self.body,0x110)[0],0xfffffffe)
        self.assertEqual(struct.unpack_from('<HH',self.body,0xc0),(0,4))
        self.assertEqual(struct.unpack_from('<Q',self.entries,72+24)[0],200)
        self.assertEqual(struct.unpack_from('<QQ',self.entries,16),(0,99))

    def test_destructor_relocation_is_followed_but_release_uses_captured_array(self):
        self.fixture();struct.pack_into('<H',self.body,0xc0,1)
        self.arrays[2]=bytearray(self.entries);self.arrays[3]=bytearray(self.entries)
        def destroy(token,flags):struct.pack_into('<Q',self.body,0xb8,2)
        def release(token):struct.pack_into('<Q',self.body,0xb8,3)
        self.run_clear(destroy=destroy,release=release)
        self.assertEqual(struct.unpack_from('<QQ',self.arrays[2],16),(0,99))
        self.assertEqual(struct.unpack_from('<QQ',self.arrays[3],16),(10,100))
        self.assertEqual(struct.unpack_from('<QQ',self.entries,16),(10,100))

    def test_captured_count_survives_callback_count_change(self):
        self.fixture()
        def notify(owner,index,key,event):
            self.events.append(index);struct.pack_into('<H',self.body,0xc0,0)
        self.run_clear(notify=notify,destroy=lambda *a:None,release=lambda *a:None)
        self.assertEqual(self.events,[2,0])
