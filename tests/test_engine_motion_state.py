import copy
import json
import unittest

from engine.motion_state import update


class MotionStateTests(unittest.TestCase):
    def test_initial_observation_does_not_invent_landing(self):
        for grounded, phase in ((True, 'grounded'), (False, 'airborne')):
            result = update({}, {'grounded': grounded}, {}, .01)
            self.assertEqual(result['phase'], phase)
            self.assertEqual(result['events'], [])
            self.assertIsNone(result['clip'])

    def test_takeoff_then_airborne_and_landing_once(self):
        state = {}
        update(state, {'grounded': True}, {}, 0)
        result = update(state, {'grounded': False}, {}, .03)
        self.assertEqual(result['phase'], 'takeoff')
        self.assertEqual(result['phase_time'], 0)
        result = update(state, {'grounded': False}, {}, .1)
        self.assertEqual(result['phase'], 'airborne')
        self.assertAlmostEqual(result['phase_time'], .02)
        result = update(state, {'grounded': True}, {}, .01)
        self.assertEqual(result['phase'], 'landing_recovery')
        for _ in range(10):
            result = update(state, {'grounded': True}, {'events': [{'type': 'landing', 'quality': 'clean'}]}, .03)
        self.assertEqual(result['phase'], 'grounded')
        self.assertEqual(state['transition_sequence'], 4)

    def test_crash_latch_does_not_restart_with_persistent_signal(self):
        state = {}
        update(state, {'grounded': False}, {}, 0)
        result = update(state, {'grounded': True}, {'crashed': True}, .1)
        self.assertEqual(result['phase'], 'crash')
        result = update(state, {'grounded': True}, {'crashed': True}, .9)
        self.assertEqual(result['phase'], 'grounded')
        result = update(state, {'grounded': True}, {'crashed': True}, .1)
        self.assertEqual(result['events'], [])
        update(state, {'grounded': True}, {'crashed': False}, .01)
        result = update(state, {'grounded': True}, {'crashed': True}, .01)
        self.assertEqual(result['phase'], 'crash')

    def test_loss_of_support_interrupts_landing_recovery(self):
        state = {}
        update(state, {'grounded': False}, {}, 0)
        update(state, {'grounded': True}, {}, .01)
        result = update(state, {'grounded': False}, {}, .01)
        self.assertEqual(result['phase'], 'takeoff')

    def test_clip_mapping_quality_and_inputs_immutable(self):
        state = {}
        body = {'grounded': False, 'velocity': [1, 2, 3]}
        diagnostics = {'events': [{'type': 'landing', 'quality': 'sketchy'}]}
        config = {'clips': {'landing_recovery': 'normal', 'landing_sketchy': 'absorb'}}
        update(state, body, {}, 0, config)
        body['grounded'] = True
        before = copy.deepcopy((body, diagnostics, config))
        result = update(state, body, diagnostics, .02, config)
        self.assertEqual(result['clip'], 'absorb')
        self.assertEqual((body, diagnostics, config), before)

    def test_zero_duration_has_bounded_two_events(self):
        state = {}
        config = {'takeoff_duration': 0, 'landing_duration': 0, 'crash_duration': 0}
        update(state, {'grounded': True}, {}, 0, config)
        for grounded in (False, True, False, True):
            result = update(state, {'grounded': grounded}, {}, .01, config)
            self.assertEqual(len(result['events']), 2)
            self.assertEqual(result['phase'], 'grounded' if grounded else 'airborne')

    def test_zero_dt_validation_does_not_consume_edge(self):
        state = {}
        update(state, {'grounded': True}, {}, 0)
        before = copy.deepcopy(state)
        result = update(state, {'grounded': False}, {'crashed': True}, 0)
        self.assertEqual(state, before)
        self.assertEqual(result['events'], [])
        result = update(state, {'grounded': False}, {'crashed': True}, .01)
        self.assertEqual(result['phase'], 'crash')

    def test_checkpoint_equivalent_continuation(self):
        state = {}
        update(state, {'grounded': True}, {}, 0)
        update(state, {'grounded': False}, {}, .05)
        restored = json.loads(json.dumps(state))
        for grounded, dt in [(False, .04), (False, .1), (True, .01), (True, .4)]:
            self.assertEqual(update(state, {'grounded': grounded}, {}, dt),
                             update(restored, {'grounded': grounded}, {}, dt))
        self.assertEqual(state, restored)

    def test_validation_failure_is_transactional(self):
        state = {}
        update(state, {'grounded': True}, {}, 0)
        before = copy.deepcopy(state)
        cases = [({'grounded': True}, {}, float('nan'), {}),
                 ({'grounded': 1}, {}, .1, {}),
                 ({'grounded': True}, {}, .1, {'landing_duration': -.1}),
                 ({'grounded': True}, {}, .1, {'clips': {'crash': ''}}),
                 ({'grounded': True}, {'crashed': 'yes'}, .1, {})]
        for body, diagnostics, dt, config in cases:
            with self.assertRaises(ValueError):
                update(state, body, diagnostics, dt, config)
            self.assertEqual(state, before)


if __name__ == '__main__':
    unittest.main()
