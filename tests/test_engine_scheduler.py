import json
import unittest

from engine.scheduler import schedule


class SchedulerTests(unittest.TestCase):
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
        for config in ({'fixed_dt': .01}, {'mode': 'subdivision', 'policy': 2}):
            state = {}
            schedule(state, .014, config)
            restored = json.loads(json.dumps(state))
            for dt in [.001, .022, 0, .04]:
                self.assertEqual(schedule(state, dt, config), schedule(restored, dt, config))
                self.assertEqual(state, restored)

    def test_invalid_or_unsupported_does_not_mutate(self):
        for dt, config in [(float('nan'), {}), (-1, {}), (1, {'fixed_dt': 0}),
                           (.01, {'mode': 'subdivision', 'smoothing_enabled': True}),
                           (1, {'mode': 'subdivision', 'max_steps': 1})]:
            state = {}
            with self.assertRaises(ValueError):
                schedule(state, dt, config)
            self.assertEqual(state, {})


if __name__ == '__main__':
    unittest.main()
