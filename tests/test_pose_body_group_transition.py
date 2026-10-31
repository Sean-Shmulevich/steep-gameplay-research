import struct
import unittest
from engine.pose_body_group_transition import transition_pose_body_group
from engine.pose_body_quiet_state import reset_pose_body_quiet_state


class BodyGroupTransitionTests(unittest.TestCase):
    def run_case(self, *, group=22, flags=8, priority=0x8000, predicates=(0,0), admit=1, mutate=False):
        c=bytearray(0x420);b=bytearray(0x200);m=bytearray(0x60)
        struct.pack_into('<QQ',c,0x408,11,22)
        struct.pack_into('<Q',b,0x10,group);struct.pack_into('<Q',b,0x30,3)
        struct.pack_into('<f',b,0x28,5);b[0x1a0:0x1b8]=bytes(range(24))
        struct.pack_into('<H',m,0x50,priority);m[0x52]=flags;m[0x53]=0xa2
        events=[];answers=iter(predicates)
        def predicate(*args):
            events.append(('predicate',*args))
            if mutate:struct.pack_into('<Q',b,0x10,99)
            return next(answers)
        def remove(*args):
            events.append(('remove',*args));struct.pack_into('<Q',b,0x10,0)
        def virtual(*args):events.append(('virtual',*args));return admit
        def obtain(*args):events.append(('obtain',*args));return 33
        def reset(*args):events.append(('reset',*args));reset_pose_body_quiet_state(b,m)
        def append(*args):events.append(('append',*args));struct.pack_into('<Q',b,0x10,args[0])
        transition_pose_body_group(c,b,context_token=1,body_token=2,metadata={3:m},
            predicate=predicate,remove_body=remove,body_virtual8=virtual,obtain_group=obtain,
            reset_body=reset,append_body=append,finalize=lambda *a:events.append(('finalize',*a)))
        return events,b,m

    def test_disabled_gate_only_finalizes(self):
        events,_,_=self.run_case(flags=0,predicates=())
        self.assertEqual(events,[('finalize',1,22)])

    def test_equal_membership_retains_captured_group_after_callback_mutation(self):
        events,b,_=self.run_case(predicates=(1,),mutate=True)
        self.assertEqual(events,[('predicate',1,2),('finalize',1,22)])
        self.assertEqual(struct.unpack_from('<Q',b,0x10)[0],99)

    def test_raw_noncanonical_predicate_forces_reassignment(self):
        events,_,_=self.run_case(predicates=(2,2))
        self.assertEqual(events,[('predicate',1,2),('remove',1,2),('virtual',2,1),
            ('predicate',1,2),('append',22,2),('finalize',1,22)])

    def test_rejected_admission_finalizes_reloaded_group(self):
        events,_,_=self.run_case(admit=0)
        self.assertEqual(events,[('predicate',1,2),('remove',1,2),('virtual',2,1),('finalize',1,0)])

    def test_nonpriority_selects_first_special_group_without_second_predicate(self):
        events,_,m=self.run_case(priority=0,predicates=(0,))
        self.assertEqual(events[-2:],[('append',11,2),('finalize',1,11)])
        self.assertEqual(m[0x53],0xa2)

    def test_ordinary_selection_composes_known_quiet_reset_preserves_motion(self):
        events,b,m=self.run_case()
        self.assertEqual(events[-4:],[('obtain',1),('reset',2),('append',33,2),('finalize',1,33)])
        self.assertEqual(m[0x53],0xa0);self.assertEqual(b[0x28:0x2c],bytes(4))
        self.assertEqual(b[0x1a0:0x1b8],bytes(range(24)))
