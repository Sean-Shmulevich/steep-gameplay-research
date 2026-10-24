import unittest

from engine.snow_velocity_correction import assemble_velocity_decay_rates
from reference.central_impulse import f32


class DecayDriveSelectionTests(unittest.TestCase):
    def case(self,**changes):
        from engine.snow_velocity_correction import select_velocity_decay_drive
        args=dict(product_a=-1,product_b=1,retention_byte=0,override_value=0,
                  drive_value=2,runtime_scale=3,override_inhibit_byte=0)
        args.update(changes)
        return select_velocity_decay_drive(**args)

    def test_negative_product_suppression_and_nonboolean_retention(self):
        self.assertEqual(self.case()['additive_rate'],0)
        self.assertEqual(self.case(retention_byte=255)['selected_drive'],4)
        self.assertEqual(self.case(product_a=0)['selected_drive'],4)

    def test_direct_override_and_independent_speed_floor_bypass(self):
        direct=self.case(override_value=.5)
        self.assertEqual(direct['additive_rate'],.5)
        self.assertEqual(direct['selected_drive'],.5)
        self.assertTrue(direct['inline_configuration_selected'])
        inhibited=self.case(override_value=.5,override_inhibit_byte=2)
        self.assertEqual(inhibited['selected_drive'],4)
        self.assertFalse(inhibited['inline_configuration_selected'])
        self.assertTrue(inhibited['speed_floor_bypassed'])


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
