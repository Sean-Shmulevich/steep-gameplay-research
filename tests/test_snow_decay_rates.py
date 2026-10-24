import unittest

from engine.snow_velocity_correction import assemble_velocity_decay_rates
from reference.central_impulse import f32


class DecayRateAssemblyTests(unittest.TestCase):
    def test_xy_gain_follows_clamps_and_does_not_scale_z(self):
        result=assemble_velocity_decay_rates(.25,2,-2,.1,3,[0]*4)
        self.assertEqual(result['rates'],[3,3,.25,0])
        self.assertFalse(result['contact_correction_disabled'])

    def test_all_four_components_and_strict_threshold(self):
        epsilon=f32(.00001)
        normal=assemble_velocity_decay_rates(1,0,0,0,2,[epsilon,-epsilon,0,epsilon])
        suppressed=assemble_velocity_decay_rates(1,0,0,0,2,[0,0,0,.000010000001])
        self.assertEqual(normal['rates'],[2,2,1,0])
        self.assertFalse(normal['contact_correction_disabled'])
        self.assertTrue(suppressed['contact_correction_disabled'])
        self.assertEqual(suppressed['rates'],[f32(.02),f32(.02),f32(.01),0])
