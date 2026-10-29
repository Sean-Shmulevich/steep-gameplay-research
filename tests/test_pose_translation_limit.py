import struct
import unittest
from engine.pose_constraint_translation import build_pose_translation_limit_pair
from reference.central_impulse import f32


def build(first,second,phase=1,single=True):
    c=bytearray(b'\x5a'*0x2000)
    struct.pack_into('<I',c,0x16c,0x400);struct.pack_into('<I',c,0x180,4)
    struct.pack_into('<f',c,0xc,2.);struct.pack_into('<I',c,0x38,phase<<27)
    for cat in (8,9):
        struct.pack_into('<I',c,0x40+cat*4,(cat-8)*32);struct.pack_into('<I',c,0xa4+cat*4,0)
    rows=build_pose_translation_limit_pair(c,single=single,body_indices=[0x10002,0x20003],
        axis=[1,0,0,0],point_a=[0]*4,point_b=[0]*4,arm_a=[0,1,0,0],arm_b=[0,0,1,0],
        first_bound=first,second_bound=second)
    return c,rows


class TranslationLimitTests(unittest.TestCase):
    def test_exact_zero_prevents_phase_gain(self):
        c,rows=build([0,1,1,1],[0]*4,phase=0)
        self.assertEqual(struct.unpack_from('<4f',c,rows[0]+16),(-0.,-2,-2,-2))

    def test_w_excluded_from_gate_but_gets_response(self):
        c,rows=build([1,1,1,-10],[-1,-1,-1,10])
        self.assertEqual(struct.unpack_from('<4f',c,rows[0]+16),(f32(-.8),)*3+(8.,))
        self.assertEqual(c[rows[0]+16:rows[0]+32],c[rows[1]+16:rows[1]+32])

    def test_only_normal_phase_scales_positive_error(self):
        for phase in (0,2,3):
            c,rows=build([1]*4,[-1]*4,phase=phase)
            self.assertEqual(struct.unpack_from('<4f',c,rows[0]+16),(0.,)*4)

    def test_opposite_axes_indices_and_caches(self):
        c,rows=build([1]*4,[-1]*4,single=False)
        self.assertEqual(rows,(0x600,0x680))
        for i,r in enumerate(rows):
            self.assertEqual(struct.unpack_from('<HHI',c,r),(2,3,4+i))
            self.assertEqual(c[r+0x40:r+0x50],b'\x5a'*16)
            self.assertEqual(c[r+0x50:r+0x58],bytes(8))
            self.assertEqual(c[r+0x58:r+0x60],b'\x5a'*8)
            self.assertEqual(c[r+0x60:r+0x70],bytes(16))
        self.assertEqual(struct.unpack_from('<f',c,rows[1]+0x20)[0],-1)
        self.assertEqual(struct.unpack_from('<I',c,0xc8)[0],2)
        self.assertEqual(struct.unpack_from('<I',c,0x180)[0],6)
