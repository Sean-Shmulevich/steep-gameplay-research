import copy
import dataclasses
import json
import threading
import unittest

from engine.control import SchedulerController
from engine.runtime import Engine
from engine.replay import record, replay


class ControllerTests(unittest.TestCase):
    def test_step_frame_runs_recovered_smoothing_plan_and_remains_paused(self):
        controller = SchedulerController({'scheduler': {'mode': 'subdivision', 'smoothing_enabled': True}})
        token = controller.pause()
        result = controller.step_frame_once(token, .016666667, {'steer': .1})
        self.assertEqual(result['state']['tick'], 2)
        self.assertTrue(result['state']['paused'])
        plan = result['state']['scheduler']['last_plan']
        self.assertEqual(plan['count'], 2)
        self.assertEqual(plan['history']['count'], 1)
        self.assertEqual(plan['steps'][0]['derivative_dt'], 2 * plan['steps'][0]['elapsed_dt'])
        frames = [row for row in result['trace']['records'] if row['kind'] == 'frame_planned']
        self.assertEqual(len(frames), 1)
        self.assertEqual(len(frames[0]['steps']), 2)
        before = controller.checkpoint()
        recording = controller.export_replay()
        self.assertEqual(controller.checkpoint(), before)
        self.assertEqual(replay(recording).state_hash(), recording['expected_hash'])
        self.assertEqual(controller.step_frame_once(token, 0)['state']['tick'], 2)

    def test_pause_step_resume_and_replay(self):
        engine = Engine()
        controller = SchedulerController(engine=engine)
        token = controller.pause()
        result = controller.step_once(token, {'steer': .2})
        self.assertEqual(result['state']['tick'], 1)
        self.assertTrue(result['state']['paused'])
        self.assertTrue(result['control']['submissions_excluded'])
        self.assertEqual(engine.state_hash(), replay(record(engine)).state_hash())
        controller.resume(token)
        self.assertEqual(controller.submit_frame(1/60)['state']['tick'], 3)
        self.assertEqual(engine.state_hash(), replay(record(engine)).state_hash())

    def test_stale_cross_controller_and_immutable_tokens(self):
        controller = SchedulerController()
        first = controller.pause()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            first.generation = 9
        other = SchedulerController().pause()
        with self.assertRaises(ValueError):
            controller.step_once(other)
        controller.resume(first)
        second = controller.pause()
        with self.assertRaises(ValueError):
            controller.step_once(first)
        third = controller.reset()
        with self.assertRaises(ValueError):
            controller.resume(second)
        self.assertEqual(controller.step_once(third)['state']['tick'], 1)

    def test_snapshot_does_not_advance_and_drained_is_not_exclusion(self):
        controller = SchedulerController()
        before = controller.checkpoint()
        for _ in range(4):
            snapshot = controller.snapshot()
            self.assertTrue(snapshot['control']['drained'])
            self.assertFalse(snapshot['control']['submissions_excluded'])
            snapshot['state']['body']['position'][0] = 999
        self.assertEqual(controller.checkpoint(), before)
        controller.pause()
        with self.assertRaises(RuntimeError):
            controller.submit_frame(.01)

    def test_failed_input_or_frame_rolls_back_and_closes_gate(self):
        controller = SchedulerController()
        before = controller.snapshot()
        with self.assertRaises(ValueError):
            controller.submit_frame(float('nan'), {'steer': .3})
        after = controller.snapshot()
        self.assertEqual(after['state']['body'], before['state']['body'])
        self.assertEqual(after['state']['input_generation'], 0)
        self.assertTrue(after['state']['paused'])
        self.assertEqual(len(after['incidents']), 1)
        self.assertTrue(after['control']['submissions_excluded'])

    def test_failed_step_invalidates_token_and_preserves_paused_state(self):
        controller = SchedulerController({'scheduler': {'fixed_dt': .1}})
        token = controller.pause()
        with self.assertRaises(ValueError):
            controller.step_once(token)
        with self.assertRaises(ValueError):
            controller.step_once(token)
        snapshot = controller.snapshot()
        self.assertEqual(snapshot['state']['tick'], 0)
        self.assertTrue(snapshot['state']['paused'])
        self.assertTrue(snapshot['control']['drained'])

    def test_competing_submission_cannot_enter_during_paused_step(self):
        engine = Engine()
        controller = SchedulerController(engine=engine)
        token = controller.pause()
        entered, release, submit_started, submit_finished = [threading.Event() for _ in range(4)]
        original = engine.step
        def blocked_step(count):
            entered.set()
            if not release.wait(2):
                raise RuntimeError('fixture release timeout')
            return original(count)
        engine.step = blocked_step
        failures = []
        def stepping():
            try:
                controller.step_once(token)
            except Exception as exc:
                failures.append(exc)
        def submitting():
            submit_started.set()
            try:
                controller.submit_frame(.01)
            except Exception as exc:
                failures.append(exc)
            finally:
                submit_finished.set()
        step_thread = threading.Thread(target=stepping)
        submit_thread = threading.Thread(target=submitting)
        step_thread.start()
        try:
            self.assertTrue(entered.wait(2))
            submit_thread.start()
            self.assertTrue(submit_started.wait(2))
            self.assertFalse(submit_finished.is_set())
        finally:
            release.set()
            step_thread.join(2)
            if submit_thread.ident is not None:
                submit_thread.join(2)
        self.assertFalse(step_thread.is_alive())
        self.assertFalse(submit_thread.is_alive())
        self.assertEqual(len(failures), 1)
        self.assertIn('excluded', str(failures[0]))
        self.assertEqual(controller.snapshot()['state']['tick'], 1)

    def test_pause_waits_for_existing_submission(self):
        engine = Engine()
        controller = SchedulerController(engine=engine)
        entered, release, paused = [threading.Event() for _ in range(3)]
        original = engine.advance
        errors = []
        def blocked(dt):
            entered.set()
            if not release.wait(2):
                raise RuntimeError('fixture timeout')
            return original(dt)
        engine.advance = blocked
        def submit():
            try:
                controller.submit_frame(1/120)
            except Exception as exc:
                errors.append(exc)
        def pause():
            controller.pause()
            paused.set()
        worker = threading.Thread(target=submit)
        pauser = threading.Thread(target=pause)
        worker.start()
        try:
            self.assertTrue(entered.wait(2))
            pauser.start()
            self.assertFalse(paused.is_set())
        finally:
            release.set()
            worker.join(2)
            if pauser.ident is not None:
                pauser.join(2)
        self.assertEqual(errors, [])
        self.assertTrue(paused.is_set())
        self.assertEqual(controller.snapshot()['state']['tick'], 1)
        self.assertTrue(controller.snapshot()['control']['submissions_excluded'])

    def test_checkpoint_restores_full_bookkeeping_and_invalidates_token(self):
        controller = SchedulerController()
        controller.submit_frame(1/60, {'steer': .1})
        token = controller.pause()
        checkpoint = json.loads(json.dumps(controller.checkpoint()))
        controller.step_once(token)
        new_token = controller.restore(checkpoint)
        self.assertEqual(controller.checkpoint(), checkpoint)
        with self.assertRaises(ValueError):
            controller.step_once(token)
        copy_controller = SchedulerController()
        copy_token = copy_controller.restore(checkpoint)
        self.assertEqual(controller.step_once(new_token)['state'], copy_controller.step_once(copy_token)['state'])

    def test_invalid_reset_restore_does_not_revoke_valid_token(self):
        controller = SchedulerController()
        token = controller.pause()
        before = controller.checkpoint()
        with self.assertRaises(ValueError):
            controller.reset({'body': {'mass': -1}})
        corrupt = copy.deepcopy(before)
        corrupt['engine_aux']['last_good']['body']['mass'] = -1
        with self.assertRaises(ValueError):
            controller.restore(corrupt)
        self.assertEqual(controller.checkpoint(), before)
        self.assertEqual(controller.step_once(token)['state']['tick'], 1)

    def test_callback_reentry_rejects_without_deadlocking(self):
        engine = Engine()
        controller = SchedulerController(engine=engine)
        engine.advance = lambda dt: controller.pause()
        with self.assertRaisesRegex(RuntimeError, 'reentry'):
            controller.submit_frame(.01)
        self.assertTrue(controller.snapshot()['control']['submissions_excluded'])


if __name__ == '__main__':
    unittest.main()
