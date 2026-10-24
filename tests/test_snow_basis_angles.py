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

    def test_preferred_reuse_does_not_request_math_or_direction(self):
        from engine.snow_basis_angles import apply_preferred_basis
        def unused(*args): raise AssertionError('unused service')
        basis=[[2,0,0,0],[0,3,0,0],[0,0,4,0]]
        r=apply_preferred_basis(basis,None,None,1,0,9,unused,unused,unused)
        self.assertEqual(r['basis'],basis)
        self.assertEqual(r['secondary_angle'],1)
        self.assertEqual(r['clear_secondary_byte'],9)

    def test_preferred_uses_negative_angle_and_ignores_other_saved_axes(self):
        from engine.snow_basis_angles import apply_preferred_basis
        r=apply_preferred_basis([[2,0,0,0],[9,9,9,9],[8,8,8,8]],
                                [0,3,0,0],math.pi/2,0,1,3,
                                math.sin,math.cos,lambda n:1/math.sqrt(n))
        expected=[[0,-1,0,0],[3,0,0,0],[0,0,1,0]]
        for actual,want in zip(r['basis'],expected):
            for a,b in zip(actual,want):self.assertAlmostEqual(a,b,places=5)
        self.assertEqual(r['clear_secondary_byte'],3)
