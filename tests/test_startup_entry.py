"""Startup entry policy and loop with synthetic screens/host samples; no game or Wine."""
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import startup_entry as se

IN_WORLD = {'ready': True, 'advancing': True, 'player_flags': 3}
ACQUIRED = {'ready': True, 'advancing': True, 'player_flags': 1, 'position': [1.0, 2.0, 3.0]}  # idle spawn
NO_PLAYER = {'ready': True, 'advancing': True, 'player_error': 'no_player'}


class PolicyTests(unittest.TestCase):
    def test_existing_transition_keys_only(self):
        for state, scan in [('title', 28), ('offline_notice', 28), ('tutorial', 28), ('map', 50)]:
            with self.subTest(state=state):
                self.assertEqual(se.Policy().step(state, None, 0), ('send', scan))

    def test_no_input_on_unrecognized_or_gameplay_screens(self):
        p = se.Policy()
        for state in ('unknown', 'capture_timeout', 'gameplay'):
            self.assertEqual(p.step(state, NO_PLAYER, 0)[0], 'wait')
        self.assertEqual(p.inputs, {})

    def test_hud_alone_is_not_gameplay(self):
        p = se.Policy()
        for native in (None, {'error': 'ConnectionRefusedError'}, NO_PLAYER,
                       {'ready': True, 'advancing': False, 'player_flags': 3},
                       {'ready': True, 'advancing': True, 'player_flags': 0}):
            self.assertEqual(p.step('gameplay', native, 0), ('wait', 'hud_without_native_confirmation'))

    def test_gameplay_needs_consecutive_native_confirmations(self):
        p = se.Policy(confirmations=2)
        self.assertEqual(p.step('gameplay', IN_WORLD, 0)[0], 'wait')
        self.assertEqual(p.step('gameplay', NO_PLAYER, 1)[0], 'wait')  # streak resets
        self.assertEqual(p.step('gameplay', IN_WORLD, 2)[0], 'wait')
        self.assertEqual(p.step('gameplay', IN_WORLD, 3), ('entered', None))

    def test_retry_waits_then_aborts_after_bound(self):
        p = se.Policy(retry=5, max_inputs=2)
        self.assertEqual(p.step('title', None, 0), ('send', 28))
        self.assertEqual(p.step('title', None, 4.9), ('wait', 'transition_pending'))
        self.assertEqual(p.step('title', None, 5.0), ('send', 28))
        self.assertEqual(p.step('title', None, 10.0)[0], 'abort')

    def test_new_screen_is_not_delayed_by_previous_retry_window(self):
        p = se.Policy(retry=5)
        p.step('title', None, 0)
        self.assertEqual(p.step('intro', None, 1), ('wait', 'intro'))
        self.assertEqual(p.step('offline_notice', None, 1), ('send', 28))

    def test_idle_spawn_without_in_world_is_accepted(self):
        p = se.Policy(confirmations=2)
        self.assertEqual(p.step('gameplay', ACQUIRED, 0)[0], 'wait')
        self.assertEqual(p.step('gameplay', ACQUIRED, 1), ('entered', None))
        self.assertIsNone(p.first_in_world_state)

    def test_records_screens_when_player_acquired_and_in_world(self):
        p = se.Policy()
        p.step('offline_notice', NO_PLAYER, 0)
        p.step('unknown', ACQUIRED, 1)
        p.step('map', ACQUIRED, 2)
        p.step('gameplay', IN_WORLD, 3)
        self.assertEqual((p.first_player_state, p.first_in_world_state), ('unknown', 'gameplay'))

    def test_classify_gameplay_hud_before_legacy(self):
        legacy = lambda text: ('map', 50)
        self.assertEqual(se.classify('change sport binoculars drop zones', legacy), 'gameplay')
        self.assertEqual(se.classify('drop zones', legacy), 'map')


class FakeGame:
    def __init__(self, frames):
        self.frames = list(frames); self.sent = []; self.fail_send = False; self.player_reads = []

    def screen(self, i, timeout):
        state, native = self.frames[min(i, len(self.frames) - 1)]
        self.native_next = native
        if state == 'timeout':
            raise subprocess.TimeoutExpired('capture', timeout)
        return ('' if state == 'unknown' else state.upper()), ('unknown' if state == 'intro' else state)

    def native(self, want_player=True):
        self.player_reads.append(want_player)
        return self.native_next

    def send(self, i, scan):
        self.sent.append((i, scan))
        return (False, 'input exit 1') if self.fail_send else (True, None)


class Clock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t
    def sleep(self, s): self.t += s + 1.0  # capture and OCR also take time


class NavigateTests(unittest.TestCase):
    def run_frames(self, frames, budget=200, fail_send=False, policy=None):
        game = FakeGame(frames); game.fail_send = fail_send; clock = Clock()
        return se.navigate(game, budget, clock=clock, sleep=clock.sleep, policy=policy), game

    def test_intro_key_presses_visible_pre_title_screens_only(self):
        frames = [('unknown', None)] * 2 + [('intro', None)] * 12 + [('title', None), ('intro', NO_PLAYER),
                  ('offline_notice', ACQUIRED), ('map', ACQUIRED), ('gameplay', ACQUIRED), ('gameplay', ACQUIRED)]
        result, game = self.run_frames(frames, policy=se.Policy(intro_key=28))
        intro = [x for x in result['inputs'] if x['state'] == 'intro']
        self.assertEqual(len(intro), se.MAX_INTRO_INPUTS)
        self.assertTrue(all(b['t'] - a['t'] >= se.INTRO_INTERVAL_SECONDS for a, b in zip(intro, intro[1:])))
        self.assertEqual([x['state'] for x in result['inputs'][len(intro):]], ['title', 'offline_notice', 'map'])
        self.assertIsNotNone(result['title_first_t'])
        self.assertEqual(result['outcome'], 'entered')

    def test_no_intro_inputs_by_default_and_player_reads_deferred(self):
        frames = [('intro', None)] * 3 + [('title', None), ('gameplay', ACQUIRED), ('gameplay', ACQUIRED)]
        result, game = self.run_frames(frames)
        self.assertEqual([x['state'] for x in result['inputs']], ['title'])
        self.assertEqual(game.player_reads, [False] * 4 + [True, True])

    def test_full_startup_sequence_enters_with_native_confirmation(self):
        frames = [('unknown', {'error': 'ConnectionRefusedError'}), ('unknown', {'ready': False}),
                  ('title', {'ready': True, 'advancing': True, 'player_error': 'no_player'}),
                  ('unknown', NO_PLAYER), ('unknown', ACQUIRED), ('offline_notice', ACQUIRED), ('map', ACQUIRED),
                  ('gameplay', ACQUIRED), ('gameplay', ACQUIRED)]
        result, game = self.run_frames(frames)
        self.assertEqual(result['outcome'], 'entered')
        self.assertTrue(result['gameplay_hud_observed'] and result['gameplay_native_verified'])
        self.assertEqual([s for _, s in game.sent], [28, 28, 50])
        self.assertEqual(result['first_player_acquired_screen'], 'unknown')
        self.assertIsNone(result['first_player_in_world_screen'])
        self.assertFalse(result['gameplay_inputs_sent'])

    def test_hud_without_player_exhausts_budget_without_inputs(self):
        result, game = self.run_frames([('gameplay', NO_PLAYER)], budget=30)
        self.assertEqual(result['outcome'], 'budget_exhausted')
        self.assertTrue(result['gameplay_hud_observed'])
        self.assertFalse(result['gameplay_native_verified'])
        self.assertEqual(game.sent, [])

    def test_stuck_screen_aborts_with_bounded_inputs(self):
        result, game = self.run_frames([('title', None)])
        self.assertTrue(result['outcome'].startswith('abort'))
        self.assertEqual(len(game.sent), se.MAX_INPUTS_PER_STATE)

    def test_input_failure_stops_navigation(self):
        result, game = self.run_frames([('title', None)], fail_send=True)
        self.assertEqual(result['outcome'], 'input_failed: input exit 1')
        self.assertEqual(len(game.sent), 1)

    def test_capture_timeout_is_recorded_not_fatal(self):
        frames = [('timeout', None), ('gameplay', IN_WORLD), ('gameplay', IN_WORLD)]
        result, _ = self.run_frames(frames)
        self.assertEqual(result['screens'][0]['state'], 'capture_timeout')
        self.assertEqual(result['outcome'], 'entered')

    def test_spawn_recorded_and_checked(self):
        frames = [('gameplay', ACQUIRED)] * 2
        result, _ = self.run_frames(frames)
        self.assertEqual(result['spawn_position'], [1.0, 2.0, 3.0])
        self.assertNotIn('spawn_matches_expected', result)
        game = FakeGame(frames); clock = Clock()
        ok = se.navigate(game, 60, clock=clock, sleep=clock.sleep, expect_spawn=[1.005, 2.0, 3.0])
        self.assertEqual((ok['outcome'], ok['spawn_matches_expected']), ('entered', True))
        game = FakeGame(frames); clock = Clock()
        moved = se.navigate(game, 60, clock=clock, sleep=clock.sleep, expect_spawn=[1.5, 2.0, 3.0])
        self.assertEqual(moved['outcome'], 'entered_unexpected_spawn')

    def test_spawn_match_rejects_missing_position(self):
        self.assertFalse(se.spawn_matches(None, [0, 0, 0], 1))
        self.assertFalse(se.spawn_matches([0, 0], [0, 0, 0], 1))

    def test_budget_bounds_cli(self):
        with self.assertRaises(SystemExit):
            se.main(['/nonexistent/out', '20'])


if __name__ == '__main__':
    unittest.main()
