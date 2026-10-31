import struct
import unittest
from engine.pose_body_events import dispatch_pose_body_event


def fixture(callbacks):
    registry=bytearray(16);struct.pack_into('<QII',registry,0,1,len(callbacks),8)
    rows=bytearray([0xa5]*128)
    for i,(callback,enabled) in enumerate(callbacks):struct.pack_into('<QB',rows,i*16,callback,enabled)
    return registry,rows,bytearray(0x2800)


class BodyEventTests(unittest.TestCase):
    def test_append_receives_same_event_then_stable_disabled_compaction(self):
        registry,rows,tls=fixture([(10,1),(20,1),(30,1)]);calls=[]
        def invoke(fn,body,event):
            self.assertEqual(tls[0x27bd],1);calls.append((fn,body,event))
            if fn==10:
                rows[8]=0;rows[16+8]=0;tls[0x27bc]=1
                struct.pack_into('<QB',rows,48,40,1);struct.pack_into('<I',registry,8,4)
        dispatch_pose_body_event(100,0x10000000a,tls=tls,get_registry=lambda:registry,listener_arrays={1:rows},invoke=invoke)
        self.assertEqual(calls,[(10,100,10),(30,100,10),(40,100,10)])
        self.assertEqual(struct.unpack_from('<I',registry,8)[0],2)
        self.assertEqual([struct.unpack_from('<Q',rows,i*16)[0] for i in range(2)],[30,40])
        self.assertEqual(tls[0x27bc:0x27be],b'\0\0')
        self.assertEqual(struct.unpack_from('<Q',rows,48)[0],40)

    def test_registry_replacement_uses_same_next_index(self):
        registry,rows,tls=fixture([(10,1),(20,1)])
        other,other_rows,_=fixture([(30,1),(40,1),(50,1)]);struct.pack_into('<Q',other,0,2)
        current=[registry];calls=[]
        def invoke(fn,b,e):calls.append(fn);current[0]=other
        dispatch_pose_body_event(1,10,tls=tls,get_registry=lambda:current[0],listener_arrays={1:rows,2:other_rows},invoke=invoke)
        self.assertEqual(calls,[10,40,50])

    def test_disabled_rows_persist_without_cleanup_request(self):
        registry,rows,tls=fixture([(10,0),(20,0)]);before=bytes(rows)
        dispatch_pose_body_event(1,10,tls=tls,get_registry=lambda:registry,listener_arrays={1:rows},invoke=lambda *a:self.fail('disabled'))
        self.assertEqual(rows,before);self.assertEqual(struct.unpack_from('<I',registry,8)[0],2)

    def test_nested_dispatch_does_not_restore_outer_dispatch_flag(self):
        registry,rows,tls=fixture([(10,1)]);observed=[]
        def invoke(fn,b,e):
            if e==10:
                dispatch_pose_body_event(b,11,tls=tls,get_registry=lambda:registry,listener_arrays={1:rows},invoke=invoke)
                observed.append(tls[0x27bd])
        dispatch_pose_body_event(1,10,tls=tls,get_registry=lambda:registry,listener_arrays={1:rows},invoke=invoke)
        self.assertEqual(observed,[0])
