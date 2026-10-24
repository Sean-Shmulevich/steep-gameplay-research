import math
import struct
import unittest
from engine.pose_body_integration import integrate_pose_body, ANGULAR_THRESHOLD
from engine.pose_body_secondary_update import apply_pose_secondary_body_state


def fixture():
    b=bytearray([0xa5]*0x200)
    for off,v in [(0x40,[1,0,0]),(0x50,[0,1,0]),(0x60,[0,0,1]),
                  (0x70,[10,20,30]),(0x128,[0,0,0]),
                  (0x1a0,[2,3,4]),(0x1ac,[0,0,0])]:
        struct.pack_into('<3f',b,off,*v)
    return b


class BodyIntegrationTests(unittest.TestCase):
    def test_translation_preserves_motion_and_padding(self):
        b=fixture();before=bytes(b)
        integrate_pose_body(b,.5)
        self.assertEqual(struct.unpack_from('<3f',b,0x70),(11,21.5,32))
        self.assertEqual(b[:0x70],before[:0x70])
        self.assertEqual(b[0x7c:],before[0x7c:])

    def test_angular_threshold_does_not_reorthonormalize(self):
        b=fixture();struct.pack_into('<f',b,0x40,2)
        struct.pack_into('<f',b,0x1ac,ANGULAR_THRESHOLD)
        integrate_pose_body(b,1)
        self.assertEqual(struct.unpack_from('<f',b,0x40)[0],2)

    def test_rotation_preserves_offset_center(self):
        b=fixture();struct.pack_into('<3f',b,0x128,1,0,0)
        struct.pack_into('<3f',b,0x1a0,0,0,0)
        struct.pack_into('<3f',b,0x1ac,0,0,math.pi/2)
        integrate_pose_body(b,1,half_angle_trig=lambda h:(math.sin(h),math.cos(h)))
        position=struct.unpack_from('<3f',b,0x70)
        first=struct.unpack_from('<3f',b,0x40)
        for actual,expected in zip([position[i]+first[i] for i in range(3)],(11,20,30)):
            self.assertAlmostEqual(actual,expected,places=5)
        self.assertAlmostEqual(first[1],1,places=6)

    def test_secondary_update_changes_transform_and_restores_motion(self):
        b=fixture();motion=bytes(b[0x1a0:0x1b8])
        state=struct.pack('<8f',1,0,-2,99,0,0,0,88)
        apply_pose_secondary_body_state([1],bodies={1:b},body_state=[state],
            update_body=lambda token,raw,s:integrate_pose_body(raw,s))
        self.assertEqual(struct.unpack_from('<3f',b,0x70),(11,20,28))
        self.assertEqual(b[0x1a0:0x1b8],motion)

    def test_rotation_requires_explicit_scalar_library_service(self):
        b=fixture();struct.pack_into('<f',b,0x1ac,1)
        with self.assertRaises(ValueError):integrate_pose_body(b,1)
