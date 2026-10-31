import struct
import unittest
from engine.pose_body_controller_events import dispatch_pose_body_controller_event
from engine.pose_body_quiet_state import reset_pose_body_quiet_state


class ControllerEventTests(unittest.TestCase):
    def setUp(self):
        self.body=bytearray(0x200);self.meta=bytearray(0x60);self.owner=bytearray(0x40);self.controller=bytearray(0x80)
        struct.pack_into('<Q',self.body,0x30,2);struct.pack_into('<Q',self.meta,0x20,3)
        struct.pack_into('<Q',self.owner,0x20,4);struct.pack_into('<QQ',self.controller,0x20,5,6)
        self.events=[]
    def run_event(self,event,invoke=None):
        dispatch_pose_body_controller_event(self.body,event,body_token=1,metadata={2:self.meta},owners={3:self.owner},
            controllers={4:self.controller},invoke=invoke or (lambda *a:self.events.append(a)))

    def test_event1_composes_known_quiet_reset_and_preserves_motion(self):
        struct.pack_into('<H',self.meta,0x50,0x8000);self.meta[0x53]=0xa1
        struct.pack_into('<f',self.body,0x28,9.);self.body[0x1a0:0x1b8]=bytes(range(24))
        def invoke(name,*args):
            self.events.append((name,*args))
            if name=='body_virtual28':reset_pose_body_quiet_state(self.body,self.meta)
        self.run_event(1,invoke)
        self.assertEqual(self.body[0x28:0x2c],bytes(4));self.assertEqual(self.meta[0x53],0xa0)
        self.assertEqual(self.body[0x1a0:0x1b8],bytes(range(24)))
        self.assertEqual(self.events,[('enter',84),('body_virtual28',1),('controller_virtuala8',6,0),('leave',84)])

    def test_event0_stamp_precedes_refresh_and_announcement_reloads_priority(self):
        struct.pack_into('<I',self.controller,0x4c,123)
        def invoke(name,*args):
            self.events.append((name,*args))
            if name=='refresh_body':
                self.assertEqual(struct.unpack_from('<I',self.meta,0x1c)[0],123)
                struct.pack_into('<H',self.meta,0x50,0x8000)
        self.run_event(0,invoke)
        self.assertEqual(self.events,[('enter',84),('refresh_body',1),('controller_virtuala8',6,0),('leave',84)])

    def test_tree_and_provider_gates(self):
        self.meta[0x52]=8
        def invoke(name,*args):
            self.events.append((name,*args))
            if name=='get_tree':return 99
        self.run_event(3,invoke)
        self.assertEqual(self.events,[('enter',84),('get_tree',5),('remove_tree',99,1),('leave',84)])
        self.events=[];self.meta[0x52]=1;self.run_event(4)
        self.assertEqual(self.events,[('enter',84),('leave',84)])

    def test_ignored_lifecycle_events_do_not_traverse_body(self):
        for event in (10,11,12):
            dispatch_pose_body_controller_event(bytearray(),event,body_token=1,metadata={},owners={},controllers={},invoke=None)
        self.run_event(99)
        self.assertEqual(self.events,[('enter',84),('leave',84)])
