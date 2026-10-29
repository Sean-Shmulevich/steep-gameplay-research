import struct
import unittest
from engine.pose_solver_layout import initialize_pose_solver_storage,plan_pose_solver_layout
from engine.pose_link_arena import solve_pose_contact_secondary_correction


class SecondaryContactPhaseTests(unittest.TestCase):
    def fixture(self,iterations):
        plan=plan_pose_solver_layout([0]*25,1);arena=bytearray(plan['size'])
        initialize_pose_solver_storage(arena,[0]*25,1)
        struct.pack_into('<I',arena,0x38,0x28000000|(iterations<<16)|12)
        arena[0xc:0x14]=struct.pack('<2f',.2,5)
        start=plan['body_state_offset'];arena[start:start+32]=struct.pack('<8f',*range(8))
        view=memoryview(arena)
        args=dict(links={},bodies={},payloads={},body_data=[view[plan['body_data_offset']:plan['body_data_offset']+64]],
                  body_state=[view[start:start+32]])
        return arena,args

    def test_absent_secondary_gate_is_byte_preserving(self):
        arena,args=self.fixture(0);before=bytes(arena)
        self.assertFalse(solve_pose_contact_secondary_correction(arena,[],**args))
        self.assertEqual(arena,before)

    def test_transition_clears_state_and_restores_special_scalars(self):
        arena,args=self.fixture(2);scalars=bytes(arena[0xc:0x14])
        self.assertTrue(solve_pose_contact_secondary_correction(arena,[],**args))
        self.assertEqual(args['body_state'][0],bytes(32))
        flags=struct.unpack_from('<I',arena,0x38)[0]
        self.assertEqual(flags&0x18000000,0x10000000)
        self.assertEqual(flags&0x20000000,0x20000000)
        self.assertEqual(arena[0xc:0x14],scalars)
