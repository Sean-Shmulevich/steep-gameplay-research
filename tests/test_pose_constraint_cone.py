import math
import struct
import unittest
from engine.pose_constraint_cone import build_pose_cone_constraint,_inverse_target
from engine.pose_constraint_build import build_pose_constraints


def fixture(paired=False,twist=False,drive=False):
    c=bytearray(0x5000);r=bytearray(0x150)
    struct.pack_into('<I',c,0x16c,0x400)
    for category,start in ((10,0),(11,0x80),(8,0x100),(9,0x180),(12,0x200),(13,0x280)):
        struct.pack_into('<I',c,0x40+4*category,start)
    struct.pack_into('<I',c,0x38,0x08000008);struct.pack_into('<2f',c,0xc,2.5,.25)
    struct.pack_into('<2Q',r,8,1,2)
    for off,v in ((0x90,(1,0,0)),(0xa0,(1,0,0)),(0xb0,(0,1,0)),(0xc0,(0,1,0))):struct.pack_into('<3f',r,off,*v)
    struct.pack_into('<2f',r,0xd0,.5,.75);r[0xd8]=twist;struct.pack_into('<f',r,0xdc,.4)
    r[0xe0]=drive;struct.pack_into('<2f',r,0xe4,2.,.5)
    for i in range(3):struct.pack_into('<f',r,0xf0+16*i+4*i,1.)
    struct.pack_into('<5f',r,0x130,.4,1e12,1.,1e12,1.)
    bodies={1:bytearray(0x140),2:bytearray(0x140)};meta={10:bytearray(0x60),20:bytearray(0x60)}
    for token,b in bodies.items():
        struct.pack_into('<Q',b,0x30,token*10);struct.pack_into('<H',b,0x1c,token-1)
        for i in range(3):struct.pack_into('<f',b,0x40+16*i+4*i,1.)
    struct.pack_into('<H',meta[20],0x50,0x8000 if paired else 0)
    return c,r,dict(bodies=bodies,metadata=meta,atan2=math.atan2)


class ConeTests(unittest.TestCase):
    def test_row_counts_and_endpoint_layouts(self):
        for paired in (False,True):
            for twist in (False,True):
                for drive in (False,True):
                    c,r,args=fixture(paired,twist,drive)
                    self.assertEqual(build_pose_cone_constraint(c,r,**args),1)
                    for cat,count in ((11 if paired else 10,1),(9 if paired else 8,5 if twist else 1),(13 if paired else 12,int(drive))):
                        self.assertEqual(struct.unpack_from('<I',c,0xa4+4*cat)[0],count)
                    self.assertEqual(struct.unpack_from('<I',c,0x180)[0],2+4*twist+drive)

    def test_drive_gates_notification(self):
        for drive,suppress in ((False,False),(True,False),(True,True)):
            c,r,args=fixture(drive=drive);r[0xe1]=suppress
            struct.pack_into('<Q',args['bodies'][1],0x10,1);struct.pack_into('<Q',args['metadata'][10],0x20,1)
            calls=[];build_pose_cone_constraint(c,r,notify=lambda *x:calls.append(x),**args)
            self.assertEqual(calls,[(1,2)] if drive and not suppress else [])

    def test_dispatch_matches_direct_builder(self):
        c,r,args=fixture(True,True,True);d=bytearray(c)
        build_pose_cone_constraint(c,r,**args)
        build_pose_constraints(d,[7],constraints={7:r},get_kind=lambda _:5,**args)
        self.assertEqual(c,d)

    def test_scalar_target_inverse_near_unit_determinant(self):
        matrix=[[1.,0,0,0],[0,1.,0,0],[0,0,1.0000001192092896,0]]
        inverse=_inverse_target(matrix)
        self.assertEqual(inverse[2][2],1.)
        self.assertGreater(inverse[0][0],1.)
        self.assertEqual(_inverse_target([[2.,0,0,0],[0,1.,0,0],[0,0,1.,0]])[0][0],.5)
