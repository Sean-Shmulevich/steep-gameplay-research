import math
import struct
import unittest
from engine.pose_constraint_vector_drive import build_pose_vector_drive_row
from engine.pose_scalar_asin import pose_scalar_asin
from reference.central_impulse import f32

IDENTITY = [[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.]]
ROT_X = [[1.,0.,0.,0.],[0.,0.,1.,0.],[0.,-1.,0.,0.]]


def build(**overrides):
    c = bytearray(b'\x5a'*0x1000)
    struct.pack_into('<2f',c,0xc,1.,.5)
    struct.pack_into('<I',c,0x16c,0x400)
    struct.pack_into('<I',c,0x180,7)
    for cat,start in ((12,0),(13,16)):
        struct.pack_into('<I',c,0x40+cat*4,start)
        struct.pack_into('<I',c,0xa4+cat*4,0)
    args=dict(single=True,cap=[10]*4,strength=[4,50,60,70],gain=[1]*4,
              frame_a=ROT_X,frame_b=IDENTITY,output_frame=IDENTITY,additive=[0]*4)
    args.update(overrides)
    before=bytes(c)
    row=build_pose_vector_drive_row(c,**args)
    return c,row,struct.unpack_from('<4f',c,row+16),before


class VectorDriveTests(unittest.TestCase):
    def test_equal_frames_leave_only_additive_and_strength(self):
        _,_,v,_=build(frame_a=IDENTITY,additive=[1,2,3,99])
        self.assertEqual(v,(1,2,3,2))

    def test_negative_gain_sign_and_axis(self):
        _,_,v,_=build()
        self.assertAlmostEqual(v[0],-math.pi/2,places=6)
        self.assertEqual(v[1:],(0,0,2))

    def test_all_xyz_cap_gate(self):
        _,_,full,_=build(cap=[.25]*4)
        self.assertEqual(full[0],-.25)
        _,_,mixed,_=build(cap=[.25,10,.25,0])
        self.assertAlmostEqual(mixed[0],-math.pi/2,places=6)

    def test_output_frame_then_additive(self):
        frame=[[0,1,0,0],[1,0,0,0],[0,0,1,0]]
        _,_,v,_=build(cap=[.25]*4,output_frame=frame,additive=[1,2,3,100])
        self.assertEqual(v,(1,1.75,3,2))

    def test_paired_allocation_preserves_coefficients_and_indices(self):
        c,row,_,before=build(single=False)
        self.assertEqual(row,0x500)
        self.assertEqual(struct.unpack_from('<I',c,0xd8)[0],1)
        self.assertEqual(struct.unpack_from('<I',c,0x180)[0],8)
        self.assertEqual(struct.unpack_from('<I',c,row+4)[0],7)
        self.assertEqual(c[row:row+4],before[row:row+4])
        self.assertEqual(c[row+32:row+80],before[row+32:row+80])

    def test_shortest_quaternion_sign_choice(self):
        # +170 and -170 degrees have a negative quaternion dot product.
        def rot(t):
            return [[1,0,0,0],[0,math.cos(t),math.sin(t),0],[0,-math.sin(t),math.cos(t),0]]
        _,_,v,_=build(frame_a=rot(math.radians(170)),frame_b=rot(math.radians(-170)))
        self.assertAlmostEqual(v[0],math.radians(20),places=6)

    def test_asin_boundaries_and_signed_zero(self):
        for v in (0.,-0.,2**-15,-2**-15):
            self.assertEqual(struct.pack('<f',pose_scalar_asin(v)),struct.pack('<f',v))
        for v in (-1.,-.5,.5,1.):
            self.assertAlmostEqual(pose_scalar_asin(v),math.asin(v),places=6)
        self.assertEqual(pose_scalar_asin(1.),f32(math.pi/2))
        for v in (1.01,math.nan,math.inf):
            with self.assertRaises(ValueError):pose_scalar_asin(v)
