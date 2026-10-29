import struct
import unittest
from engine.pose_constraint_translation import build_pose_translation_row
from reference.central_impulse import f32


def build(single=True,soft=False,scalar=2.,flags=8):
    c=bytearray(b'\x5a'*0x3000)
    struct.pack_into('<f',c,0xc,scalar);struct.pack_into('<I',c,0x38,flags)
    struct.pack_into('<I',c,0x16c,0x400);struct.pack_into('<I',c,0x180,3)
    for cat in (14,15,16,17):
        struct.pack_into('<I',c,0x40+4*cat,(cat-14)*32);struct.pack_into('<I',c,0xa4+4*cat,0)
    row=build_pose_translation_row(c,single=single,axis=[1,0,0,0],point_a=[0]*4,point_b=[2,0,0,9],
        arm_a=[0,1,0,0],arm_b=[0,0,1,0],**(dict(stiffness=[4]*4,damping=[1]*4) if soft else {}))
    return c,row


class TranslationTests(unittest.TestCase):
    def test_hard_gain_is_not_phase_gated(self):
        for mask in (0,1,2,3):
            c,r=build(flags=(mask<<27)|8)
            self.assertEqual(struct.unpack_from('<3f',c,r+16),tuple([f32(-1.6)]*3))

    def test_cross_coefficients_and_preserved_header(self):
        c,r=build(single=False)
        self.assertEqual(c[r:r+4],b'\x5a'*4)
        self.assertEqual(struct.unpack_from('<4f',c,r+48),(0,0,-1,0))
        self.assertEqual(struct.unpack_from('<4f',c,r+80),(0,-1,0,0))
        self.assertEqual(c[r+64:r+80],b'\x5a'*16)

    def test_soft_coefficient_and_negative_response(self):
        c,r=build(soft=True)
        self.assertEqual(struct.unpack_from('<4f',c,r+80),(1,1,1,1))
        self.assertEqual(struct.unpack_from('<3f',c,r+16),(-2,-2,-2))

    def test_soft_near_zero_keeps_stiffness(self):
        for scalar in (0.,1e-6,-1e-6):
            c,r=build(single=False,soft=True,scalar=scalar)
            self.assertEqual(struct.unpack_from('<4f',c,r+96),(4,4,4,4))

    def test_count_and_result_reservation(self):
        c,r=build(single=False,soft=True)
        self.assertEqual(struct.unpack_from('<I',c,0xe8)[0],1)
        self.assertEqual(struct.unpack_from('<I',c,0x180)[0],4)
        self.assertEqual(struct.unpack_from('<I',c,r+4)[0],3)
