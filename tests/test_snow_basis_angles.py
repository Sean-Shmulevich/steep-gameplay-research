import math
import unittest
from engine.snow_basis_angles import apply_basis_angles


class BasisAngleTests(unittest.TestCase):
    def run_angles(self, primary, secondary, rebuild, clear):
        return apply_basis_angles([[3,0,0,0],[0,2,0,0],[0,0,7,0]],
                                  primary,secondary,rebuild,clear,math.sin,math.cos,
                                  lambda n:1/math.sqrt(n))

    def test_primary_wins_and_does_not_consume_secondary(self):
        r=self.run_angles(.5,1,0,255)
        self.assertEqual(r['branch'],'primary')
        self.assertAlmostEqual(math.sqrt(sum(x*x for x in r['basis'][0][:3])),3,places=5)
        self.assertEqual(r['secondary_angle'],1)
        self.assertEqual(r['clear_secondary_byte'],255)

    def test_secondary_rebuilds_unit_axis_and_consumes_requested_angle(self):
        r=self.run_angles(0,1,128,2)
        self.assertEqual(r['branch'],'secondary')
        self.assertAlmostEqual(math.sqrt(sum(x*x for x in r['basis'][0][:3])),1,places=5)
        self.assertEqual(r['basis'][1],[0,2,0,0])
        self.assertEqual(r['secondary_angle'],0)
        self.assertEqual(r['clear_secondary_byte'],0)

    def test_secondary_can_persist_and_disabled_rebuild_retains_pending_state(self):
        r=self.run_angles(0,1,1,0)
        self.assertEqual(r['secondary_angle'],1)
        r=self.run_angles(-0.,1,0,3)
        self.assertEqual(r['branch'],'retain')
        self.assertEqual(r['basis'],[[3,0,0,0],[0,2,0,0],[0,0,7,0]])
        self.assertEqual(r['clear_secondary_byte'],3)
        r['basis'][0][0]=42
        self.assertEqual(r['saved_basis'][0][0],3)

    def test_zero_secondary_does_not_clear_flag(self):
        self.assertEqual(self.run_angles(0,-0.,1,4)['clear_secondary_byte'],4)
