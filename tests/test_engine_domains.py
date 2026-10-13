import copy
import math
import unittest

from engine.domains import step_air, step_environment, _para_forces, _response


def body(velocity=(0, 0, 0)):
    return dict(position=[0., 0., 100.], velocity=list(velocity), orientation=[0., 0., 0., 1.], angular_velocity=[0., 0., 0.], mass=20., grounded=False)


class AirTests(unittest.TestCase):
    def test_response_is_documented_trapezoid(self):
        integral, window, result = _response(2, 2, 1, 4, 1, .1)
        self.assertEqual((integral, window, result), (2.1, 1, 2.1))

    def test_ascending_force_and_zero_velocity(self):
        lift, drag, gravity = _para_forces((0, 0, 2), (0, 0, 1), 1, 1, 9.81)
        self.assertEqual(lift, [0, 0, -4])
        self.assertEqual(drag, [0, 0, 0.])
        b = body()
        step_air(b, {}, .01, {'sport': 'paraglider'})
        self.assertAlmostEqual(b['velocity'][2], -.0981)
        self.assertTrue(all(math.isfinite(x) for x in b['velocity']))

    def test_steering_and_tuck(self):
        straight, turning, tuck = body(), body(), body()
        for _ in range(60):
            step_air(straight, {}, 1/60, {})
            step_air(turning, {'steer': 1}, 1/60, {})
            step_air(tuck, {'tuck': True}, 1/60, {})
        self.assertGreater(turning['position'][1], straight['position'][1])
        self.assertGreater(tuck['velocity'][0], straight['velocity'][0])
        self.assertLess(tuck['velocity'][2], straight['velocity'][2])

    def test_wind_additive_not_accumulated(self):
        a, b = body(), body()
        for _ in range(20):
            step_air(a, {}, .01, {})
            step_air(b, {}, .01, {'wind': [1, 2, 3]})
        for i, expected in enumerate((1, 2, 3)):
            self.assertAlmostEqual(b['velocity'][i]-a['velocity'][i], expected)

    def test_paraglider_brake_and_turn(self):
        a, b, c = body((12, 0, -2)), body((12, 0, -2)), body((12, 0, -2))
        step_air(a, {}, .01, {'sport': 'paraglider'})
        step_air(b, {'brake': True}, .01, {'sport': 'paraglider'})
        step_air(c, {'steer': 1}, .01, {'sport': 'paraglider'})
        self.assertLess(b['velocity'][0], a['velocity'][0])
        self.assertGreater(c['velocity'][1], a['velocity'][1])

    def test_zero_and_invalid_dt(self):
        b = body()
        original = copy.deepcopy(b)
        step_air(b, {}, 0, {})
        self.assertEqual(b, original)
        for dt in (-1, float('nan')):
            with self.assertRaises(ValueError):
                step_air(b, {}, dt, {})
        with self.assertRaises(ValueError):
            step_air(b, {}, .1, {'response_seconds': 0})


class EnvironmentTests(unittest.TestCase):
    def test_wrap_is_single_subtraction_even_held(self):
        state = {'time_of_day': 60., 'hold_flag': True}
        step_environment(state, 1, {})
        self.assertEqual(state['time_of_day'], 24.)
        self.assertEqual(state['crossing_count'], 1)
        self.assertEqual(state['cyclic_counter'], 1)

    def test_clock_example_and_nonpositive_cycle_stop(self):
        state = {'time_of_day': 23.99}
        step_environment(state, 1, {'cycle_duration': 10})
        self.assertAlmostEqual(state['time_of_day'], .03)
        state = {'time_of_day': 60., 'stop_enabled': True, 'stop_target': 18}
        step_environment(state, 1, {'cycle_duration': 0})
        self.assertEqual(state['time_of_day'], 18)
        self.assertEqual(state['hold_count'], 1)
        self.assertEqual(state['crossing_count'], 0)

    def test_hold_and_stop(self):
        for field in ('external_hold', 'global_hold'):
            state = {'time_of_day': 12.}
            step_environment(state, 10, {field: True})
            self.assertEqual(state['time_of_day'], 12.)
        state = {'time_of_day': 12., 'stop_enabled': True, 'stop_target': 12.02}
        step_environment(state, 1, {})
        self.assertEqual(state['time_of_day'], 12.02)
        self.assertEqual(state['hold_count'], 1)
        step_environment(state, 1, {})
        self.assertEqual(state['time_of_day'], 12.02)

    def test_weather_coordinate_and_completion(self):
        state = {'start': .2, 'destination': .8, 'remaining': 6., 'duration': 10.}
        d = step_environment(state, 1, {'modifier_available': True})
        self.assertAlmostEqual(d['weather_argument'], 50.)
        d = step_environment(state, 5, {'modifier_available': True})
        self.assertEqual(d['weather_argument'], 80.)
        self.assertFalse(d['affects_snow_grip'])

    def test_weather_external_hold_and_bad_duration(self):
        state = {'remaining': 2., 'duration': 0., 'weather_scalar': .3}
        step_environment(state, 1, {'modifier_available': True, 'external_hold': True})
        self.assertEqual(state['remaining'], 2.)
        self.assertEqual(state['weather_scalar'], .3)
        with self.assertRaises(ValueError):
            step_environment(state, .1, {'modifier_available': True})

    def test_overlay_order(self):
        overlays = [{'weight': .5, 'samples': {'fog': 20}}, {'weight': .5, 'samples': {'fog': 0}}]
        a, b = {}, {}
        step_environment(a, 0, {'property_samples': {'fog': 10}, 'overlays': overlays})
        step_environment(b, 0, {'property_samples': {'fog': 10}, 'overlays': overlays[::-1]})
        self.assertEqual(a['properties']['fog'], 7.5)
        self.assertEqual(b['properties']['fog'], 12.5)


if __name__ == '__main__':
    unittest.main()
