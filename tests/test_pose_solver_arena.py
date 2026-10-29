import struct
import unittest
from engine.pose_solver_layout import initialize_pose_solver_storage
from engine.pose_solver_arena import solve_pose_arena


def fixture():
    arena=bytearray(0x800)
    counts=[0]*25;counts[10]=1
    plan=initialize_pose_solver_storage(arena,counts,1)
    row=plan['rows_offset']
    struct.pack_into('<HHI',arena,row,0,65535,0)
    struct.pack_into('<4f',arena,row+16,10,0,0,.25)
    for i in range(3):
        struct.pack_into('<4f',arena,row+0x20+i*16,*[float(i==j) for j in range(4)])
    struct.pack_into('<16f',arena,plan['body_data_offset'],1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1)
    struct.pack_into('<I',arena,0x38,4)
    return arena,plan


class SolverArenaTests(unittest.TestCase):
    def test_updates_same_allocation_with_zero_append_counter(self):
        arena,plan=fixture();tail=bytes(arena[plan['size']:])
        self.assertEqual(struct.unpack_from('<I',arena,0xa4+4*10)[0],0)
        solve_pose_arena(arena)
        self.assertEqual(struct.unpack_from('<f',arena,plan['body_state_offset'])[0],-.25)
        self.assertEqual(struct.unpack_from('<f',arena,plan['results_offset'])[0],-.25)
        self.assertEqual(arena[plan['size']:],tail)

    def test_special_phase_preserves_point_rows_and_scalar_bits(self):
        arena,plan=fixture()
        struct.pack_into('<I',arena,0x38,0x10030000)
        arena[0xc:0x14]=bytes.fromhex('000000804523c17f')
        before=bytes(arena)
        solve_pose_arena(arena)
        self.assertEqual(bytes(arena),before)

    def test_missing_result_storage_is_rejected(self):
        arena,plan=fixture()
        del arena[plan['results_offset']+15:]
        with self.assertRaises(ValueError):solve_pose_arena(arena)

    def test_partial_body_record_is_rejected(self):
        arena,plan=fixture()
        struct.pack_into('<I',arena,0x174,plan['body_state_offset']+1)
        with self.assertRaises(ValueError):solve_pose_arena(arena)
