import struct
import unittest
from engine.pose_constraint_commands import build_pose_command_constraint


class CommandConstraintTests(unittest.TestCase):
    def fixture(self):
        c=bytearray(b'Z'*0x1000)
        for off,v in [(0x16c,0x400),(0xa0,0),(0x104,0),(0x180,7)]:struct.pack_into('<I',c,off,v)
        r=bytearray(0x300);struct.pack_into('<2Q',r,8,1,0)
        struct.pack_into('<i',r,0x74,1)
        for i in range(16):struct.pack_into('<I',r,0x78+i*4,0x80000000+i)
        b=bytearray(0x40);struct.pack_into('<H',b,0x1c,3)
        return c,r,{1:b}

    def test_expansion_swaps_endpoint_vectors_and_preserves_bits(self):
        c,r,b=self.fixture();r[0x59]=128
        self.assertEqual(build_pose_command_constraint(c,r,bodies=b),1)
        self.assertEqual(struct.unpack_from('<2HI',c,0x400),(3,0,7))
        for j,k in enumerate((2,3,0,1)):
            self.assertEqual(c[0x430+j*16:0x440+j*16],r[0x78+k*12:0x84+k*12]+bytes(4))
        self.assertEqual(c[0x470:0x480],r[0xa8:0xac]*4)
        self.assertEqual(c[0x408:0x420],b'Z'*24)
        self.assertEqual(struct.unpack_from('<I',c,0x180)[0],8)

    def test_negative_count_reserves_row_without_commands(self):
        c,r,b=self.fixture();struct.pack_into('<i',r,0x74,-1)
        build_pose_command_constraint(c,r,bodies=b)
        self.assertEqual(c[0x430:0x790],b'Z'*(0x790-0x430))
        self.assertEqual(struct.unpack_from('<i',c,0x424)[0],-1)
        self.assertEqual(struct.unpack_from('<I',c,0x104)[0],1)

    def test_capacity_guard_precedes_mutation(self):
        c,r,b=self.fixture();struct.pack_into('<i',r,0x74,7);before=bytes(c)
        with self.assertRaises(ValueError):build_pose_command_constraint(c,r,bodies=b)
        self.assertEqual(bytes(c),before)
