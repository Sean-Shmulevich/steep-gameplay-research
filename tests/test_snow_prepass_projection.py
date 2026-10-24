import math
import unittest
from engine.snow_prepass_projection import project_prepass_direction


class PrepassProjectionTests(unittest.TestCase):
    def project(self, selected, direction, fallback=None):
        return project_prepass_direction(selected,direction,fallback,lambda n:1/math.sqrt(n))

    def test_projection_does_not_normalize_supplied_direction(self):
        r=self.project([1,0,1,0],[0,0,2,0])
        self.assertAlmostEqual(r['axis0'][0],1/math.sqrt(10),places=6)
        self.assertAlmostEqual(r['axis0'][2],-3/math.sqrt(10),places=6)
        self.assertEqual(r['auxiliary_direction'],[0,0,2,0])

    def test_fallback_orients_by_z_sign_then_projects(self):
        a=self.project([0,0,1,0],[0,0,1,0],[2,0,1,0])
        b=self.project([0,0,1,0],[0,0,1,0],[2,0,-1,0])
        self.assertEqual(a['axis0'],[1,0,0,0])
        self.assertEqual(b['axis0'],[-1,0,0,0])
        self.assertTrue(a['used_fallback'])

    def test_w_participates_in_fallback_gate_but_not_norm(self):
        with self.assertRaises(ValueError):
            self.project([0,0,1,1],[0,0,1,0],[2,0,1,0])

    def test_zero_z_fallback_does_not_invent_a_rescue_axis(self):
        with self.assertRaises(ValueError):
            self.project([0,0,1,0],[0,0,1,0],[2,0,0,0])
