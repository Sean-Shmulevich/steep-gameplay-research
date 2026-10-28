import struct
import unittest
from engine.pose_body_quiet_state import update_pose_body_quiet_state


def fixture():
    b=bytearray(0x200);m=bytearray(0x60);m[0x53]=0xae
    return b,m


class QuietStateTests(unittest.TestCase):
    def update(self,b,m,**kw):
        args=dict(scalar=.5,duration_threshold=1,linear_threshold=2,angular_threshold=3)
        args.update(kw);update_pose_body_quiet_state(b,m,**args)

    def test_duration_is_strict_and_preserves_old_state_until_crossing(self):
        b,m=fixture()
        self.update(b,m);self.update(b,m)
        self.assertEqual(struct.unpack_from('<f',b,0x28)[0],1)
        self.assertEqual(m[0x53],0xae)
        self.update(b,m)
        self.assertEqual(m[0x53],0xa1)

    def test_motion_equality_and_inhibit_reset_timer_and_low_nibble(self):
        for field,value in ((0x1a0,2),(0x1ac,3),(0xaa,None)):
            b,m=fixture();struct.pack_into('<f',b,0x28,4)
            if value is None:b[field]=2
            else:struct.pack_into('<f',b,field,value)
            self.update(b,m)
            self.assertEqual(b[0x28:0x2c],bytes(4));self.assertEqual(m[0x53],0xa0)

    def test_per_field_override_and_negative_threshold_squared(self):
        b,m=fixture();struct.pack_into('<f',b,0x1a0,1)
        self.update(b,m,overrides=[-2,-1,.25])
        self.assertEqual(m[0x53],0xa1)
        self.update(b,m,overrides=[.5,-1,-1])
        self.assertEqual(m[0x53],0xa0)

    def test_negative_scalar_is_not_clamped(self):
        b,m=fixture();self.update(b,m,scalar=-.25)
        self.assertEqual(struct.unpack_from('<f',b,0x28)[0],-.25)
