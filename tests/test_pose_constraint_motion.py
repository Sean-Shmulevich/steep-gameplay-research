import struct
import unittest
from engine.pose_constraint_motion import build_pose_motion_constraint
from engine.pose_constraint_build import build_pose_constraints


class MotionConstraintTests(unittest.TestCase):
    def fixture(self, paired=False):
        c=bytearray(b'\xa5'*0x1000);r=bytearray(0xb0)
        for off,value in ((0x16c,0x400),(0x48,0),(0x4c,16),(0xac,0),(0xb0,0),(0x180,0)):
            struct.pack_into('<I',c,off,value)
        struct.pack_into('<f',c,0xc,2);struct.pack_into('<f',c,0x1c,0)
        struct.pack_into('<2Q',r,8,1,2);struct.pack_into('<4f',r,0xa0,1,0,0,0)
        bodies={1:bytearray(0x1c0),2:bytearray(0x1c0)}
        metadata={10:bytearray(0x60)}
        struct.pack_into('<H',metadata[10],0x50,0x8000 if paired else 0)
        for token,b in bodies.items():
            struct.pack_into('<H',b,0x1c,token-1);struct.pack_into('<Q',b,0x30,10)
            for i in range(3):struct.pack_into('<4f',b,0x40+16*i,*[float(i==j) for j in range(4)])
        return c,r,dict(bodies=bodies,metadata=metadata)

    def test_midpoint_coefficients_and_bias(self):
        for paired,row in ((False,0x400),(True,0x500)):
            c,r,args=self.fixture(paired)
            struct.pack_into('<3f',args['bodies'][2],0x70,2,4,0)
            struct.pack_into('<f',c,0x1c,.5)
            build_pose_motion_constraint(c,r,**args)
            self.assertEqual(struct.unpack_from('<4f',c,row+16),(3,)*4)
            self.assertEqual(struct.unpack_from('<3f',c,row+0x30),(0,0,2))
            if paired:self.assertEqual(struct.unpack_from('<3f',c,row+0x70),(0,0,2))
            self.assertEqual(c[row+0x40:row+0x50],b'\xa5'*16)
            self.assertEqual(struct.unpack_from('<Q',c,row+0x50)[0],0)
            self.assertEqual(struct.unpack_from('<4f',c,row+0x60),(0,)*4)

    def test_motion_does_not_create_restitution(self):
        c,r,args=self.fixture(True)
        struct.pack_into('<3f',args['bodies'][2],0x70,2,4,0)
        baseline=bytearray(c);build_pose_motion_constraint(baseline,r,**args)
        struct.pack_into('<6f',args['bodies'][1],0x1a0,100,-200,300,50,-70,90)
        struct.pack_into('<6f',args['bodies'][2],0x1a0,-300,400,-500,80,10,-60)
        build_pose_motion_constraint(c,r,**args)
        self.assertEqual(c,baseline)

    def test_single_branch_ignores_second_center_and_motion(self):
        c,r,args=self.fixture()
        baseline=bytearray(c);build_pose_motion_constraint(baseline,r,**args)
        struct.pack_into('<3f',args['bodies'][2],0x128,4,5,6)
        struct.pack_into('<6f',args['bodies'][2],0x1a0,10,20,30,40,50,60)
        build_pose_motion_constraint(c,r,**args)
        self.assertEqual(c,baseline)

    def test_dispatch_runs_kind6(self):
        c,r,args=self.fixture()
        build_pose_constraints(c,[9],constraints={9:r},get_kind=lambda t:6,**args)
        self.assertEqual(struct.unpack_from('<I',c,0xac)[0],1)
        self.assertEqual(struct.unpack_from('<I',c,0x180)[0],1)
