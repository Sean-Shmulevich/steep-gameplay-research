import struct
import unittest
from engine.pose_solver_settings import initialize_pose_solver_settings
from engine.pose_solver_layout import initialize_pose_solver_storage
from engine.pose_solver_control import run_pose_solver

class SettingsTests(unittest.TestCase):
    def test_raw_mapping_and_reciprocal(self):
        context=bytearray([0xa5]*0x190);settings=bytes(range(64));tail=bytes(context[0x3c:])
        initialize_pose_solver_settings(context,settings,scalar=2,group_token=123)
        self.assertEqual(struct.unpack_from('<2f',context,0xc),(.5,2))
        self.assertEqual(context[0x14:0x18],settings[0x2c:0x30])
        self.assertEqual(context[0x20:0x24],settings[0x18:0x1c])
        self.assertEqual(context[0x3c:],tail)
        self.assertEqual(struct.unpack_from('<Q',context,0x30)[0],123)

    def test_flag_low_bits_and_phase_reset(self):
        context=bytearray([0xff]*0x190);settings=bytearray(64)
        settings[0x21]=2;settings[0x14]=3
        struct.pack_into('<I',settings,0x24,0xfffffffe);struct.pack_into('<HH',settings,0x28,0xffff,0xffff)
        initialize_pose_solver_settings(context,settings,scalar=-2,group_token=0)
        expected=0x80000000|0x40000000|0x07ff0000|0xfffc|2
        self.assertEqual(struct.unpack_from('<I',context,0x38)[0],expected)
        self.assertEqual(struct.unpack_from('<f',context,0xc)[0],-.5)

    def test_layout_settings_and_solver_control_composition(self):
        context=bytearray(0x190);initialize_pose_solver_storage(context,[0]*25,0)
        settings=bytearray(64);struct.pack_into('<HH',settings,0x28,2,3)
        initialize_pose_solver_settings(context,settings,scalar=.5,group_token=0)
        calls=[]
        run_pose_solver(context,base_token=0,prepare=lambda d,c:calls.append('prepare'),iterate=lambda d,c:calls.append('iterate'))
        self.assertEqual(calls,['prepare','iterate','iterate'])
        self.assertEqual(struct.unpack_from('<2f',context,0xc),(2,.5))

    def test_zero_scalar_has_no_invented_reciprocal(self):
        with self.assertRaises(ValueError):initialize_pose_solver_settings(bytearray(0x190),bytes(64),scalar=0,group_token=0)
