import unittest

from engine.body_velocity_limits import initialized_velocity_limits
from engine.snow_velocity_correction import contact_return_candidate, speed


class InitializedVelocityLimitsTests(unittest.TestCase):
    def test_component_caps_do_not_limit_vector_magnitude(self):
        bounds = initialized_velocity_limits()
        result = contact_return_candidate(
            [150, -150, 150, 9], [0, 0, 1, 0], 1, 1, True,
            bounds['linear_lower'], bounds['linear_upper'])
        self.assertEqual(result['velocity'], [120, -120, 120, 0])
        self.assertGreater(speed(result['velocity']), 120)

    def test_scenario_override_does_not_mutate_initializer_defaults(self):
        bounds = initialized_velocity_limits()
        bounds['linear_upper'][0] = 5
        self.assertEqual(initialized_velocity_limits()['linear_upper'][0], 120)
        self.assertEqual(bounds['linear_upper'][1:], [120, 120])
