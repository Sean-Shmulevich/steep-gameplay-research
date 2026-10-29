import struct
import unittest
from engine.pose_solver_layout import plan_pose_solver_layout,initialize_pose_solver_storage
from engine.pose_link_arena import run_pose_contact_pass_from_bodies


class BodyContactPassTests(unittest.TestCase):
    def fixture(self):
        counts=[0]*25;plan=plan_pose_solver_layout(counts,1);arena=bytearray(plan['size'])
        initialize_pose_solver_storage(arena,counts,1)
        body=dict(index1c=0,frame=dict(basis=[[1,0,0],[0,1,0],[0,0,1]],translation=[0,0,0]),
                  metadata_flags52=0,flagsaa=0,tensor170=[[1,0,0],[0,1,0],[0,0,1]],
                  scalar124=1,motion1a0=[1,2,3],motion1ac=[4,5,6],damping1b8=None)
        raw={10:bytearray([0xa5]*0x200)}
        args=dict(links={},bodies={10:body},payloads={},resources={},profiles={},modes={},
                  body_tokens=[10],raw_bodies=raw,scalar=.5,vector=[0,0,-2])
        return arena,body,raw,args,plan

    def test_body_production_reaches_raw_motion_without_contacts(self):
        arena,b,raw,args,plan=self.fixture()
        run_pose_contact_pass_from_bodies(arena,[],**args)
        self.assertEqual(struct.unpack_from('<3f',raw[10],0x1a0),(1,2,2))
        self.assertEqual(struct.unpack_from('<3f',raw[10],0x1ac),(4,5,6))
        self.assertEqual(struct.unpack_from('<3f',arena,plan['body_state_offset']),(1,2,2))
        self.assertEqual(raw[10][:0x1a0],bytes([0xa5]*0x1a0))

    def test_external_increment_gate_and_index_guard(self):
        arena,b,raw,args,plan=self.fixture();b['flagsaa']=8
        run_pose_contact_pass_from_bodies(arena,[],**args)
        self.assertEqual(struct.unpack_from('<3f',raw[10],0x1a0),(1,2,3))
        b['index1c']=1
        with self.assertRaises(ValueError):run_pose_contact_pass_from_bodies(arena,[],**args)

    def test_damping_is_not_silently_approximated(self):
        arena,b,raw,args,plan=self.fixture();b['damping1b8']=[.1]*4
        with self.assertRaises(ValueError):run_pose_contact_pass_from_bodies(arena,[],**args)
