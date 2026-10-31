import struct
import unittest
from engine.pose_body_controller_transition import transition_controller_pose_body
from engine.pose_body_group_transition import transition_pose_body_group
from engine.pose_body_quiet_state import reset_pose_body_quiet_state


class ControllerTransitionTests(unittest.TestCase):
    def fixture(self):
        c=bytearray(0x80);b=bytearray(0x200);m=bytearray(0x60)
        struct.pack_into('<Q',c,0x30,4);struct.pack_into('<Q',b,0x10,5)
        struct.pack_into('<Q',b,0x30,3)
        return c,b,m

    def test_gates_call_no_services(self):
        for flag,group in ((1,5),(0,0),(1,0)):
            c,b,m=self.fixture();m[0x52]=flag;struct.pack_into('<Q',b,0x10,group)
            transition_controller_pose_body(c,b,controller_token=1,body_token=2,
                metadata={3:m},enter=None,leave=None,transition=None,reset_body=None)

    def test_enter_changes_context_without_rechecking_gates(self):
        c,b,m=self.fixture();events=[]
        def enter(sync):
            events.append(('enter',sync));struct.pack_into('<Q',c,0x30,44)
            struct.pack_into('<Q',b,0x10,0);m[0x52]=1
        transition_controller_pose_body(c,b,controller_token=1,body_token=2,metadata={3:m},
            enter=enter,leave=lambda *a:events.append(('leave',*a)),
            transition=lambda *a:events.append(('transition',*a)),
            reset_body=lambda *a:events.append(('reset',*a)))
        self.assertEqual(events,[('enter',0x51),('transition',44,2),('reset',2),('leave',0x51)])

    def test_joined_transition_resets_even_when_inner_selection_is_skipped(self):
        c,b,m=self.fixture();context=bytearray(0x420);m[0x53]=0xa2
        struct.pack_into('<f',b,0x28,7);b[0x1a0:0x1b8]=bytes(range(24));events=[]
        def transition(ctx,body):
            self.assertEqual((ctx,body),(4,2))
            transition_pose_body_group(context,b,context_token=ctx,body_token=body,
                metadata={3:m},predicate=None,remove_body=None,body_virtual8=None,
                obtain_group=None,reset_body=None,append_body=None,
                finalize=lambda *a:events.append(('finalize',*a)))
        def reset(body):
            events.append(('reset',body));reset_pose_body_quiet_state(b,m)
        transition_controller_pose_body(c,b,controller_token=1,body_token=2,metadata={3:m},
            enter=lambda *a:events.append(('enter',*a)),leave=lambda *a:events.append(('leave',*a)),
            transition=transition,reset_body=reset)
        self.assertEqual(events,[('enter',0x51),('finalize',4,5),('reset',2),('leave',0x51)])
        self.assertEqual(m[0x53],0xa0);self.assertEqual(b[0x28:0x2c],bytes(4))
        self.assertEqual(b[0x1a0:0x1b8],bytes(range(24)))
