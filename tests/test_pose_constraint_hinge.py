import math
import struct
import unittest
from engine.pose_constraint_hinge import build_pose_hinge_constraint


class HingeConstraintTests(unittest.TestCase):
    def fixture(self, paired=False, mode=0, swap=0):
        c=bytearray(0x5000);r=bytearray(0x100)
        struct.pack_into('<I',c,0x16c,0x400)
        for category,start in ((22,0),(23,0x80),(8,0x100),(9,0x180),(14,0x200),(15,0x280)):
            struct.pack_into('<I',c,0x40+category*4,start)
        struct.pack_into('<I',c,0x38,0x08000008)
        struct.pack_into('<2f',c,0xc,2.5,.25)
        struct.pack_into('<2Q',r,8,1,2);r[0x59]=swap
        for offset,vector in ((0x90,(1,0,0,0)),(0xa0,(1,0,0,0)),(0xb0,(0,1,0,0)),(0xc0,(0,1,0,0))):
            struct.pack_into('<4f',r,offset,*vector)
        struct.pack_into('<2f',r,0xd0,-1,1);struct.pack_into('<I',r,0xd8,mode)
        struct.pack_into('<5f',r,0xdc,.75,2,.5,1e12,1)
        bodies={1:bytearray(0x140),2:bytearray(0x140)}
        metadata={10:bytearray(0x60),20:bytearray(0x60)}
        for token,b in bodies.items():
            struct.pack_into('<H',b,0x1c,token-1);struct.pack_into('<Q',b,0x30,token*10)
            for i in range(3):struct.pack_into('<4f',b,0x40+16*i,*[float(i==j) for j in range(4)])
        struct.pack_into('<H',metadata[20],0x50,0x8000 if paired else 0)
        return c,r,dict(bodies=bodies,metadata=metadata,atan2=math.atan2)

    def test_emits_two_stage_and_two_limits(self):
        for paired,category,limit,row in ((False,22,8,0x400),(True,23,9,0xc00)):
            c,r,args=self.fixture(paired)
            struct.pack_into('<f',args['bodies'][1],0x70,2)
            self.assertEqual(build_pose_hinge_constraint(c,r,**args),1)
            self.assertEqual(struct.unpack_from('<I',c,0xa4+4*category)[0],1)
            self.assertEqual(struct.unpack_from('<I',c,0xa4+4*limit)[0],2)
            self.assertEqual(struct.unpack_from('<I',c,0x180)[0],3)
            self.assertEqual(struct.unpack_from('<3f',c,row+16),(2,0,0))
            self.assertEqual(c[row+0xf0:row+0x100],bytes(16))
            self.assertEqual(struct.unpack_from('<12f',c,row+0x80),(0,0,0,0,0,1,0,0,0,0,1,0))
            if paired:
                self.assertEqual(struct.unpack_from('<12f',c,row+0x130),(0,0,0,0,0,-1,0,0,0,0,-1,0))

    def test_swap_negates_optional_drive_sample(self):
        for swap,expected in ((0,-.75),(1,.75)):
            c,r,args=self.fixture(mode=2,swap=swap)
            build_pose_hinge_constraint(c,r,**args)
            self.assertEqual(struct.unpack_from('<4f',c,0x2410),(expected,expected,expected,.125))
            self.assertEqual(struct.unpack_from('<HHI',c,0x2400),(0,1,3))
            self.assertEqual(struct.unpack_from('<I',c,0x180)[0],4)

    def test_notification_requires_all_gates(self):
        for mode,suppress,group,owner,expected in ((2,0,1,1,True),(0,0,1,1,False),(2,1,1,1,False),(2,0,0,1,False),(2,0,1,0,False)):
            c,r,args=self.fixture(mode=mode);r[0xf0]=suppress
            struct.pack_into('<Q',args['bodies'][1],0x10,group)
            struct.pack_into('<Q',args['metadata'][10],0x20,owner)
            calls=[]
            build_pose_hinge_constraint(c,r,notify=lambda *a:calls.append(a),**args)
            self.assertEqual(calls,[(1,2)] if expected else [])

    def test_reached_notification_cannot_silently_disappear(self):
        c,r,args=self.fixture(mode=2)
        struct.pack_into('<Q',args['bodies'][1],0x10,1)
        struct.pack_into('<Q',args['metadata'][10],0x20,1)
        with self.assertRaisesRegex(ValueError,'notification'):
            build_pose_hinge_constraint(c,r,**args)

    def test_angle_service_called_once_with_geometry(self):
        c,r,args=self.fixture();seen=[]
        args['atan2']=lambda y,x:seen.append((y,x)) or 0.
        build_pose_hinge_constraint(c,r,**args)
        self.assertEqual(seen,[(0.,1.)])
