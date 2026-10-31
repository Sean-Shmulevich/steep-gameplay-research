import struct
import unittest
from engine.pose_body_owner_events import dispatch_pose_body_owner_event
from engine.pose_body_events import dispatch_pose_body_event


class BodyOwnerEventsTests(unittest.TestCase):
    def test_routes_exact_arguments_and_ignores_without_body_access(self):
        body=bytearray(0x200);struct.pack_into('<Q',body,0xb0,1234);events=[]
        def manager():events.append('manager');return 7
        for event in (10,11,12,0x10000000b,99):
            dispatch_pose_body_owner_event(1,event,bodies={1:body},get_manager=manager,
                remove_body=lambda *a:events.append(('remove',*a)),remove_link=lambda *a:events.append(('link',*a)),
                update_body=lambda *a:events.append(('update',*a)))
        self.assertEqual(events,['manager',('remove',7,1),'manager',('link',7,1234),
            'manager',('update',7,1),'manager',('link',7,1234),'manager'])
        dispatch_pose_body_owner_event(999,0,bodies={},get_manager=lambda:7,
            remove_body=None,remove_link=None,update_body=None)

    def test_registered_dispatch_composes_event10_route(self):
        registry=bytearray(16);struct.pack_into('<QII',registry,0,2,1,1)
        rows=bytearray(16);struct.pack_into('<QB',rows,0,3,1);tls=bytearray(0x2800);events=[]
        def invoke(fn,body,event):
            self.assertEqual(fn,3);self.assertEqual(tls[0x27bd],1)
            dispatch_pose_body_owner_event(body,event,bodies={},get_manager=lambda:7,
                remove_body=lambda *a:events.append(a),remove_link=None,update_body=None)
        dispatch_pose_body_event(100,10,tls=tls,get_registry=lambda:registry,listener_arrays={2:rows},invoke=invoke)
        self.assertEqual(events,[(7,100)])
