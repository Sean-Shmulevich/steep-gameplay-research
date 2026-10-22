"""Authored mod API behavior, not original-game actuation fidelity."""
import unittest
import copy
import json
from engine.control import SchedulerController
from engine.replay import replay


class SpeedModTests(unittest.TestCase):
    def controller(self, velocity=(3, 4, 0)):
        return SchedulerController({'body': {'velocity': list(velocity),
                                             'angular_velocity': [1, 2, 3]}})

    def test_boost_preserves_momentum_and_timing_and_replays(self):
        c = self.controller(); old = c.pause(); before = c.snapshot()['state']
        token = c.adjust_speed(old, 2)
        after = c.snapshot()['state']
        for key in ('tick', 'time', 'animation', 'pose', 'scheduler'):
            self.assertEqual(after[key], before[key])
        self.assertEqual(after['body']['angular_velocity'], [1, 2, 3])
        self.assertAlmostEqual(after['body']['velocity'][0], 4.2)
        self.assertAlmostEqual(after['body']['velocity'][1], 5.6)
        with self.assertRaises(ValueError): c.step_once(old)
        c.step_once(token)
        recording = c.export_replay()
        self.assertEqual(replay(recording).state_hash(), recording['expected_hash'])

    def test_brake_to_zero_and_boost_cap(self):
        c = self.controller(); token = c.adjust_speed(c.pause(), -10)
        self.assertEqual(c.snapshot()['state']['body']['velocity'], [0, 0, 0])
        before = c.checkpoint()
        with self.assertRaises(ValueError): c.adjust_speed(token, 2)
        self.assertEqual(c.checkpoint(), before)
        c = self.controller((59, 0, 0)); token = c.adjust_speed(c.pause(), 10)
        self.assertEqual(c.snapshot()['state']['body']['velocity'], [60, 0, 0])
        before = c.checkpoint()
        with self.assertRaises(ValueError): c.adjust_speed(token, 1)
        self.assertEqual(c.checkpoint(), before)
        token = c.adjust_speed(token, -2)
        self.assertEqual(c.snapshot()['state']['body']['velocity'], [58, 0, 0])
        c.resume(token)

    def test_invalid_delta_and_foreign_token_leave_state_unchanged(self):
        c = self.controller(); token = c.pause(); before = c.checkpoint()
        for delta in (True, 0, 11, -11, float('nan'), float('inf'), '2'):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                c.adjust_speed(token, delta)
            self.assertEqual(c.checkpoint(), before)
        with self.assertRaises(ValueError): c.adjust_speed(self.controller().pause(), 2)
        self.assertEqual(c.checkpoint(), before)
        c.resume(token)
        with self.assertRaises(ValueError): c.adjust_speed(token, 2)

    def test_recording_preserves_input_and_both_pulses_from_start(self):
        c = self.controller((10, 0, 0))
        c.submit_frame(1/60, {'steer': .2})
        token = c.pause()
        token = c.adjust_speed(token, 2)
        token = c.adjust_speed(token, -2)
        c.step_once(token)
        recording = json.loads(json.dumps(c.export_replay()))
        self.assertIsNone(recording['base'])
        self.assertEqual([x['delta_speed'] for x in recording['commands']
                          if x['op']=='adjust_speed'], [2, -2])
        self.assertEqual(recording['commands'][0]['op'], 'input')
        reconstructed = replay(recording)
        self.assertEqual(reconstructed.snapshot(), c.snapshot()['state'])
        self.assertEqual(reconstructed.events, c.checkpoint()['engine']['events'])
        self.assertEqual(reconstructed.commands, recording['commands'])
        broken = copy.deepcopy(recording)
        pulse = next(x for x in broken['commands'] if x['op']=='adjust_speed')
        pulse['delta_speed'] = 3
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            replay(broken)

    def test_checkpoint_continuation_retains_new_pulse_commands(self):
        c = self.controller((10, 0, 0))
        token = c.pause()
        token = c.adjust_speed(token, 2)
        saved = c.checkpoint()
        c.step_once(token)
        token = c.restore(saved)
        token = c.adjust_speed(token, -2)
        c.step_once(token)
        recording = c.export_replay()
        self.assertTrue(any(x['op']=='adjust_speed' for x in recording['commands']))
        self.assertEqual(replay(recording).snapshot(), c.snapshot()['state'])
