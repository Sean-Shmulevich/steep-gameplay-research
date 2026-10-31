import struct
import unittest
from engine.pose_body_event_registry import register_pose_body_listener,remove_pose_body_listener
from engine.pose_body_events import dispatch_pose_body_event


class BodyEventRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry=bytearray(16);self.rows={1:bytearray(128)};self.tls=bytearray(0x2800)
        struct.pack_into('<QII',self.registry,0,1,0,8)
    def add(self,fn):
        register_pose_body_listener(fn,get_registry=lambda:self.registry,listener_arrays=self.rows,grow=None,padding=b'padding')
    def remove(self,fn):
        remove_pose_body_listener(fn,tls=self.tls,get_registry=lambda:self.registry,listener_arrays=self.rows)

    def test_dispatch_self_removal_append_and_cleanup_compose(self):
        self.add(10);self.add(20);calls=[]
        def invoke(fn,b,e):
            calls.append(fn)
            if fn==10:self.remove(10);self.remove(20);self.add(30)
        dispatch_pose_body_event(1,10,tls=self.tls,get_registry=lambda:self.registry,listener_arrays=self.rows,invoke=invoke)
        self.assertEqual(calls,[10,30]);self.assertEqual(struct.unpack_from('<I',self.registry,8)[0],1)
        self.assertEqual(struct.unpack_from('<Q',self.rows[1],0)[0],30)
        self.assertEqual(self.rows[1][9:16],b'padding')

    def test_duplicate_disabled_first_match_is_not_skipped(self):
        self.add(10);self.add(10);self.tls[0x27bd]=1
        self.remove(10);self.remove(10)
        self.assertEqual(self.rows[1][8],0);self.assertEqual(self.rows[1][24],1)
        self.assertEqual(struct.unpack_from('<I',self.registry,8)[0],2)

    def test_missing_membership_raises_without_mutation(self):
        self.add(10);before=(bytes(self.registry),bytes(self.rows[1]),bytes(self.tls))
        with self.assertRaises(KeyError):self.remove(20)
        self.assertEqual(before,(bytes(self.registry),bytes(self.rows[1]),bytes(self.tls)))

    def test_growth_relocates_array_but_keeps_captured_descriptor(self):
        struct.pack_into('<II',self.registry,8,0,0);other=bytearray(16);current=[self.registry]
        def grow(registry,capacity):
            self.assertEqual(capacity,8);self.rows[2]=bytearray(128)
            struct.pack_into('<Q',registry,0,2);struct.pack_into('<I',registry,12,capacity)
            current[0]=other
        register_pose_body_listener(50,get_registry=lambda:current[0],listener_arrays=self.rows,grow=grow,padding=bytes(7))
        self.assertEqual(struct.unpack_from('<I',self.registry,8)[0],1)
        self.assertEqual(struct.unpack_from('<QB',self.rows[2],0),(50,1))
        self.assertEqual(other,bytes(16))
