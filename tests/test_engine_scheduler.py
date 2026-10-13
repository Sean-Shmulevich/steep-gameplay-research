import json
import copy
import struct
import unittest

from engine.scheduler import schedule, FREQUENCY_TABLE, native_initial_state


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def adjacent32(x, direction):
    bits = struct.unpack('<I', struct.pack('<f', x))[0]
    return struct.unpack('<f', struct.pack('<I', bits + direction))[0]


class SchedulerTests(unittest.TestCase):
    def test_native_initializer_is_not_an_executed_step(self):
        state = native_initial_state()
        self.assertEqual(state['last_count'], 0)
        self.assertEqual(state['total_substeps'], 0)
        self.assertEqual(state['last_consumed'], f32(1/90))
        self.assertEqual(state['last_elapsed'], f32(1/90))
        self.assertEqual(state['selected_frequency'], 90)
        self.assertEqual(state['history']['capacity'], 10)
        self.assertEqual(state['history']['count'], 0)
        self.assertTrue(state['smoothing_enabled'])
        self.assertNotIn('last_plan', state)

    def test_native_initializer_explicit_smoothing_continuation(self):
        state = native_initial_state()
        copy = json.loads(json.dumps(state))
        config = {'mode': 'subdivision', 'smoothing_enabled': True}
        self.assertEqual(schedule(state, 1/60, config), schedule(copy, 1/60, config))
        self.assertEqual(state, copy)
        self.assertEqual(state['selected_frequency'], 120)
        self.assertEqual(state['history']['count'], 1)

    def test_fixed_retains_partial_and_backlog(self):
        state = {}
        config = {'fixed_dt': .01, 'max_steps': 2}
        self.assertEqual(schedule(state, .005, config), [])
        self.assertEqual(len(schedule(state, .035, config)), 2)
        self.assertAlmostEqual(state['retained'], .02)
        self.assertEqual(len(schedule(state, 0, config)), 2)
        self.assertAlmostEqual(state['retained'], 0)

    def test_subdivision_separate_clocks(self):
        state = {}
        result = schedule(state, 1/60, {'mode': 'subdivision'})
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['derivative_dt'], 2 * result[0]['elapsed_dt'])
        self.assertEqual(state['retained'], 0)

    def test_nonzero_policy_retains_remainder(self):
        state = {}
        result = schedule(state, 1.4/120, {'mode': 'subdivision', 'policy': 2})
        self.assertEqual(len(result), 1)
        self.assertGreater(state['retained'], 0)
        self.assertAlmostEqual(result[0]['elapsed_dt'], 1.1/120, places=8)

    def test_tiny_interval_zero_and_below_frequency_single(self):
        self.assertEqual(schedule({}, 1e-7, {'mode': 'subdivision'}), [])
        result = schedule({}, .004, {'mode': 'subdivision'})
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]['elapsed_dt'], .004)

    def test_checkpoint_equivalence(self):
        for config in ({'fixed_dt': .01}, {'mode': 'subdivision', 'policy': 2},
                       {'mode': 'subdivision', 'policy': 2, 'smoothing_enabled': True, 'history_capacity': 3}):
            state = {}
            schedule(state, .014, config)
            restored = json.loads(json.dumps(state))
            for dt in [.001, .022, 0, .04]:
                self.assertEqual(schedule(state, dt, config), schedule(restored, dt, config))
                self.assertEqual(state, restored)

    def test_invalid_or_unsupported_does_not_mutate(self):
        for dt, config in [(float('nan'), {}), (-1, {}), (1, {'fixed_dt': 0}),
                           (.01, {'mode': 'subdivision', 'smoothing_enabled': True, 'frequency': 120}),
                           (1, {'mode': 'subdivision', 'max_steps': 1})]:
            state = {}
            with self.assertRaises(ValueError):
                schedule(state, dt, config)
            self.assertEqual(state, {})

    def test_zero_frame_updates_history_before_epsilon_exit(self):
        state = {}
        self.assertEqual(schedule(state, 0, {'mode': 'subdivision', 'smoothing_enabled': True}), [])
        self.assertEqual(state['history']['count'], 1)
        self.assertEqual(state['last_plan']['frequency_table_index'], 0)
        self.assertEqual(state['last_plan']['frequency'], 100)
        self.assertEqual(state['last_plan']['branch'], 'below_epsilon')

    def test_ring_wrap_and_uncapped_raw_frame_history(self):
        state = {}
        cfg = {'mode': 'subdivision', 'smoothing_enabled': True, 'history_capacity': 3}
        for dt in [.01, .02, .03, .5]:
            schedule(state, dt, cfg)
        history = state['history']
        self.assertEqual(history['write'], 1)
        self.assertEqual(history['oldest'], 1)
        self.assertEqual(history['values'], [f32(.5), f32(.02), f32(.03)])
        mean = f32(f32(f32(f32(.02) + f32(.03)) + f32(.5)) / f32(3))
        self.assertEqual(state['last_plan']['mean_frame_dt'], mean)
        self.assertEqual(state['last_plan']['accumulator_before_cap'], .5)
        self.assertEqual(state['last_plan']['accumulator_after_cap'], f32(.06666667014360428))
        self.assertGreater(state['last_plan']['cap_discarded'], .4)

    def test_smoothing_disable_clears_cursors_then_restarts(self):
        state = {}
        cfg = {'mode': 'subdivision', 'smoothing_enabled': True}
        schedule(state, .02, cfg)
        old = list(state['history']['values'])
        schedule(state, .01, {'mode': 'subdivision'})
        self.assertEqual(state['history']['count'], 0)
        self.assertEqual(state['history']['values'], old)
        self.assertEqual(state['last_plan']['frequency'], 120)
        schedule(state, .01, cfg)
        self.assertEqual(state['history']['count'], 1)
        self.assertEqual(state['last_plan']['mean_frame_dt'], f32(.01))

    def test_policy_one_overrides_after_smoothing(self):
        state = {}
        schedule(state, .016, {'mode': 'subdivision', 'policy': 1, 'smoothing_enabled': True})
        self.assertEqual(state['history']['count'], 1)
        self.assertEqual(state['last_plan']['frequency'], 90)
        self.assertEqual(state['last_plan']['frequency_table_index'], 12)

    def test_all_frequency_table_indices(self):
        self.assertEqual(len(FREQUENCY_TABLE), 13)
        for index in range(1, 13):
            state = {}
            schedule(state, .2/index, {'mode': 'subdivision', 'smoothing_enabled': True})
            self.assertEqual(state['last_plan']['frequency_table_index'], index)
            self.assertEqual(state['last_plan']['frequency'], FREQUENCY_TABLE[index])

    def test_strict_epsilon_and_round_up_boundaries(self):
        cfg = {'mode': 'subdivision'}
        epsilon = f32(9.999999747378752e-6)
        self.assertEqual(schedule({}, adjacent32(epsilon, -1), cfg), [])
        self.assertEqual(len(schedule({}, epsilon, cfg)), 1)
        midpoint = f32(1.5/120)
        self.assertEqual(len(schedule({}, adjacent32(midpoint, -1), cfg)), 1)
        self.assertEqual(len(schedule({}, midpoint, cfg)), 2)

    def test_plan_serializable_and_not_aliased_to_returned_steps(self):
        state = {}
        result = schedule(state, 1/60, {'mode': 'subdivision'})
        plan = copy.deepcopy(state['last_plan'])
        self.assertEqual(plan['steps'], result)
        self.assertEqual(json.loads(json.dumps(state)), state)
        result[0]['elapsed_dt'] = 99
        self.assertEqual(state['last_plan'], plan)
        self.assertEqual(state['frame_count'], 1)
        self.assertEqual(state['total_substeps'], 2)

    def test_error_after_ring_append_is_transactional(self):
        state = {}
        cfg = {'mode': 'subdivision', 'smoothing_enabled': True}
        schedule(state, .01, cfg)
        before = copy.deepcopy(state)
        with self.assertRaises(ValueError):
            schedule(state, .06, dict(cfg, max_steps=1))
        self.assertEqual(state, before)
        with self.assertRaises(ValueError):
            schedule(state, .01, dict(cfg, history_capacity=4))
        self.assertEqual(state, before)

    def test_observer_counters_not_execution_and_override_labeled(self):
        state = {}
        schedule(state, 0, {'mode': 'subdivision', 'frequency': 60})
        self.assertEqual(state['frame_count'], 1)
        self.assertEqual(state['total_substeps'], 0)
        self.assertIn('designed', state['evidence'])
        self.assertEqual(state['last_plan']['frequency_source'], 'designed_frequency_override')

    def test_corrupt_history_and_boolean_policy_rejected(self):
        state = {}
        schedule(state, .01, {'mode': 'subdivision', 'smoothing_enabled': True})
        state['history']['write'] = 0
        before = copy.deepcopy(state)
        with self.assertRaises(ValueError):
            schedule(state, .01, {'mode': 'subdivision', 'smoothing_enabled': True})
        self.assertEqual(state, before)
        with self.assertRaises(ValueError):
            schedule({}, .01, {'mode': 'subdivision', 'policy': True})


if __name__ == '__main__':
    unittest.main()
