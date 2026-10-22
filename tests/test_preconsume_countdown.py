import unittest
from reference.central_impulse import advance_preconsume_countdown, f32


class PreconsumeCountdownTests(unittest.TestCase):
    def test_expired_countdown_keeps_decreasing(self):
        self.assertEqual(advance_preconsume_countdown(-1,.125),-1.125)

    def test_crosses_zero_without_clamping(self):
        self.assertEqual(advance_preconsume_countdown(.125,.25),-.125)

    def test_rounds_each_substep_instead_of_one_outer_subtraction(self):
        initial=f32(.333); elapsed=f32(.01)
        value=initial
        for _ in range(3): value=advance_preconsume_countdown(value,elapsed)
        self.assertEqual(value,f32(f32(f32(initial-elapsed)-elapsed)-elapsed))
        self.assertNotEqual(value,advance_preconsume_countdown(initial,f32(3*elapsed)))
