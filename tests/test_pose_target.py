import math
import struct
import unittest
from engine.pose_constraint_target import prepare_pose_target_frame


def fixture():
    c=bytearray(0xd4)
    for off,col in ((0x20,(1,0,0)),(0x30,(1,0,0)),(0x40,(0,1,0)),(0x50,(0,1,0)),
                    (0x80,(1,0,0)),(0x90,(0,1,0)),(0xa0,(0,0,1))):struct.pack_into('<3f',c,off,*col)
    struct.pack_into('<2f',c,0x60,.5,.75)
    struct.pack_into('<f',c,0x6c,.2)
    return c,bytearray(b'\x5a'*48)


class TargetTests(unittest.TestCase):
    def test_identity_copy_and_padding(self):
        c,d=fixture()
        prepare_pose_target_frame(c,d,swapped=False,atan2=math.atan2)
        for i in range(3):
            self.assertEqual(d[16*i:16*i+12],c[0x80+16*i:0x8c+16*i])
            self.assertEqual(d[16*i+12:16*i+16],b'\x5a'*4)

    def test_swapped_changes_measurement_not_initial_copy(self):
        c,d=fixture()
        for off,col in ((0x80,(0,1,0)),(0x90,(-1,0,0)),(0xa0,(0,0,1))):struct.pack_into('<3f',c,off,*col)
        calls=[]
        def service(y,x):calls.append((y,x));return 0.
        prepare_pose_target_frame(c,d,swapped=True,atan2=service)
        for i in range(3):self.assertEqual(d[16*i:16*i+12],c[0x80+16*i:0x8c+16*i])
        self.assertEqual(len(calls),1)

    def test_secondary_gate_controls_angle_evaluation(self):
        c,d=fixture();calls=[]
        def service(y,x):calls.append((y,x));return 0.
        prepare_pose_target_frame(c,d,swapped=False,atan2=service)
        self.assertEqual(len(calls),1)
        c[0x68]=1;calls.clear()
        prepare_pose_target_frame(c,d,swapped=False,atan2=service)
        self.assertEqual(len(calls),2)

    def test_native_sign_convention_is_not_world_angle_clamp(self):
        c,d=fixture();t=1.
        for off,col in ((0x80,(math.cos(t),math.sin(t),0)),(0x90,(-math.sin(t),math.cos(t),0))):struct.pack_into('<3f',c,off,*col)
        prepare_pose_target_frame(c,d,swapped=False,atan2=math.atan2)
        x,y,_=struct.unpack_from('<3f',d)
        self.assertAlmostEqual(math.atan2(y,x),1.25,places=6)
        for i in range(3):self.assertEqual(d[16*i+12:16*i+16],b'\x5a'*4)
