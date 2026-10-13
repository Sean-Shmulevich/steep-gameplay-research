import json
import math
import unittest

from engine import scoring


class ScoringTests(unittest.TestCase):
    def test_rotation_quantization_preserves_float32_boundary(self):
        self.assertEqual(scoring.rotation_points(math.radians(225), math.radians(405), math.radians(44)), 15)
        self.assertEqual(scoring.rotation_points(2*math.pi), 10)

    def test_landing_commits_once(self):
        state = {}
        scoring.begin_air(state)
        scoring.update_air(state, [0, 0, 2*math.pi], 1)
        self.assertEqual(state['pending'], 10)
        event = scoring.land(state)[0]
        self.assertEqual(event['points'], 10)
        self.assertEqual(scoring.land(state), [])
        self.assertEqual(state['total'], 10)

    def test_crash_and_short_jump_cancel_without_erasing_total(self):
        state = {'total': 30}
        for dt, clean in [(1, False), (.1, True)]:
            scoring.begin_air(state)
            scoring.update_air(state, [0, 0, 20], dt)
            self.assertEqual(scoring.land(state, clean)[0]['type'], 'score_cancelled')
        self.assertEqual(state['total'], 30)

    def test_commit_truncation(self):
        state = {}
        scoring.begin_air(state)
        state.update(pending=1, air_time=1)
        self.assertEqual(scoring.land(state, config={'multiplier': 2.75})[0]['points'], 2)

    def test_checkpoint_restores_inflight_detector(self):
        state = {}
        body = {'grounded': False, 'angular_velocity': [0, 0, math.pi]}
        scoring.update(state, body, {}, .5)
        copy = json.loads(json.dumps(state))
        for target in (state, copy):
            scoring.update(target, body, {}, .5)
            scoring.update(target, {'grounded': True}, {}, .01)
        self.assertEqual(state, copy)
        self.assertGreater(state['total'], 0)

    def test_reset_and_invalid_values(self):
        state = {'total': 10}
        scoring.reset(state, keep_total=True)
        self.assertEqual(state['total'], 10)
        scoring.reset(state)
        self.assertEqual(state['total'], 0)
        with self.assertRaises(ValueError):
            scoring.update_air(state, [0, float('inf'), 0], .1)
        with self.assertRaises(ValueError):
            scoring.rotation_points(float('nan'))


if __name__ == '__main__':
    unittest.main()
