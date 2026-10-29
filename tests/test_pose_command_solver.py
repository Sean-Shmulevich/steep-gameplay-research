import struct
import unittest
from engine.pose_command_solver import prepare_pose_command_row,iterate_pose_command_row


class CommandSolverTests(unittest.TestCase):
    def fixture(self,single=True):
        row=bytearray(912);row[0x20]=int(single);struct.pack_into('<i',row,0x24,1)
        for off in (0x30,0x50):struct.pack_into('<4f',row,off,1,0,0,0)
        for off,val in [(0x70,2),(0x80,-1),(0x90,1),(0xa0,.25)]:struct.pack_into('<4f',row,off,*([val]*4))
        data=bytearray(64)
        for i in range(3):struct.pack_into('<4f',data,i*16,*[float(i==j) for j in range(4)])
        struct.pack_into('<4f',data,48,1,1,1,1)
        return row,[data],[bytearray(32)]

    def test_prepare_cached_impulse_then_bounded_iteration(self):
        row,data,state=self.fixture()
        prepare_pose_command_row(row,body_data=data,body_state=state)
        self.assertEqual(struct.unpack_from('<4f',row,0x330),(-1,-1,-1,0))
        self.assertEqual(struct.unpack_from('<f',state[0])[0],.25)
        iterate_pose_command_row(row,body_data=data,body_state=state)
        self.assertEqual(struct.unpack_from('<f',state[0])[0],1)
        self.assertEqual(struct.unpack_from('<f',row,0xa0)[0],1)

    def test_same_body_endpoint_updates_accumulate(self):
        row,data,state=self.fixture(False)
        prepare_pose_command_row(row,body_data=data,body_state=state)
        self.assertEqual(struct.unpack_from('<f',row,0x330)[0],-.5)
        self.assertEqual(struct.unpack_from('<f',state[0])[0],.5)
        iterate_pose_command_row(row,body_data=data,body_state=state)
        self.assertEqual(struct.unpack_from('<f',state[0])[0],1.5)

    def test_zero_effective_mass_is_explicitly_unsupported(self):
        row,data,state=self.fixture();data[0][:]=bytes(64)
        with self.assertRaises(ValueError):prepare_pose_command_row(row,body_data=data,body_state=state)
