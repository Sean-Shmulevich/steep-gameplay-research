import unittest
from reference.input_profile import preset_weight,blend


class InputProfileTests(unittest.TestCase):
    def test_converted_thresholds_and_gradual_interior(self):
        self.assertEqual(preset_weight(0),0)
        self.assertEqual(preset_weight(7/3.6),0)
        self.assertEqual(preset_weight(9.5/3.6),.5)
        self.assertEqual(preset_weight(12/3.6),0.9999998211860657)
        self.assertEqual(preset_weight(3.3333335),1)
        self.assertGreater(preset_weight(2.5),0)
        self.assertLess(preset_weight(2.5),1)
        self.assertEqual(preset_weight(7),1)

    def test_branch_priority_handles_equal_and_reversed_thresholds(self):
        self.assertEqual(preset_weight(0,7,7),0)
        self.assertEqual(preset_weight(10,7,7),1)
        self.assertEqual(preset_weight(9/3.6,12,7),0)
        self.assertEqual(preset_weight(13/3.6,12,7),1)

    def test_blend_does_not_clamp_supplied_weight(self):
        self.assertEqual(blend(2,10,0),2)
        self.assertEqual(blend(2,10,1),10)
        self.assertEqual(blend(2,10,.5),6)
        self.assertEqual(blend(2,10,2),18)
