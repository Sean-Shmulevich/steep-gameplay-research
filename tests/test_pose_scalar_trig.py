import struct
import unittest
from engine.pose_scalar_trig import small_angle_sin_cos
from engine.pose_body_integration import integrate_pose_body


class ScalarTrigTests(unittest.TestCase):
    def test_signed_zero_and_finite_domain(self):
        self.assertEqual(struct.pack('<f',small_angle_sin_cos(-0.)[0]),struct.pack('<f',-0.))
        self.assertEqual(small_angle_sin_cos(0.),(0.,1.))
        for x in (1.,float('inf'),float('nan')):
            with self.assertRaises(ValueError):small_angle_sin_cos(x)
        last=struct.unpack('<f',struct.pack('<I',0x3f490fda))[0]
        self.assertGreater(small_angle_sin_cos(last)[1],0)
        next_value=struct.unpack('<f',struct.pack('<I',0x3f490fdb))[0]
        with self.assertRaises(ValueError):small_angle_sin_cos(next_value)

    def test_body_rotation_runs_without_recorded_trig(self):
        body=bytearray(0x200)
        for off,v in ((0x40,[1,0,0]),(0x50,[0,1,0]),(0x60,[0,0,1]),(0x1ac,[0,0,.5])):
            struct.pack_into('<3f',body,off,*v)
        integrate_pose_body(body,1.,half_angle_trig=small_angle_sin_cos)
        first=struct.unpack_from('<3f',body,0x40)
        self.assertAlmostEqual(first[0],.87758256,places=6)
        self.assertAlmostEqual(abs(first[1]),.47942554,places=6)
        self.assertAlmostEqual(sum(v*v for v in first),1.,places=6)

    def test_reduced_quadrants_and_common_range(self):
        from engine.pose_scalar_trig import scalar_sin_cos
        for x,expected in ((1.,(.84147098,.54030231)),(2.,(.90929743,-.41614684)),
                           (4.,(-.7568025,-.65364362)),(-2.,(-.90929743,-.41614684))):
            actual=scalar_sin_cos(x)
            for a,b in zip(actual,expected):self.assertAlmostEqual(a,b,places=6)
        self.assertEqual(scalar_sin_cos(.5),small_angle_sin_cos(.5))
        for x in (500000.,-500000.,float('inf')):
            with self.assertRaises(ValueError):scalar_sin_cos(x)
        last=struct.unpack('<f',struct.pack('<I',0x48f423ff))[0]
        self.assertTrue(all(abs(v)<=1 for v in scalar_sin_cos(last)))
