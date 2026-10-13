import unittest

from engine.animation import default_resources
from engine.control import SchedulerController
from engine.replay import replay


class ControlledMutationTests(unittest.TestCase):
    def assert_replay(self, controller):
        recording = controller.export_replay()
        self.assertEqual(replay(recording).state_hash(), recording['expected_hash'])

    def test_tuning_preserves_state_excludes_submissions_and_replaces_token(self):
        controller = SchedulerController({'execution_mode': 'mixed'})
        controller.submit_frame(1/60)
        old = controller.pause()
        before = controller.snapshot()['state']
        changes = {'physics': {'brake_deceleration': 4}}
        token = controller.tune(old, changes)
        changes['physics']['brake_deceleration'] = 999
        self.assertEqual(controller.snapshot()['state'], before)
        self.assertEqual(controller.checkpoint()['engine']['scenario']['physics']['brake_deceleration'], 4)
        with self.assertRaises(ValueError):
            controller.step_once(old)
        with self.assertRaises(RuntimeError):
            controller.submit_frame(.01)
        controller.step_once(token, {'brake': True})
        self.assert_replay(controller)

    def test_failed_validation_preserves_checkpoint_and_current_token(self):
        controller = SchedulerController()
        token = controller.pause()
        before = controller.checkpoint()
        with self.assertRaises(ValueError):
            controller.tune(token, {'physics': {'spring_mass': 0}})
        self.assertEqual(controller.checkpoint(), before)
        with self.assertRaises(ValueError):
            controller.replace_resources(token, {'category': 'unknown', 'rig': {}, 'clips': {}})
        self.assertEqual(controller.checkpoint(), before)
        controller.step_once(token)

    def test_resource_replacement_preserves_body_and_replays(self):
        controller = SchedulerController()
        old = controller.pause()
        controller.step_once(old)
        before = controller.snapshot()['state']
        rig, clips = default_resources()
        token = controller.replace_resources(old, dict(category='synthetic', rig=rig, clips=clips))
        after = controller.snapshot()['state']
        self.assertEqual(after['body'], before['body'])
        self.assertEqual(after['tick'], before['tick'])
        self.assertTrue(after['paused'])
        with self.assertRaises(ValueError):
            controller.resume(old)
        controller.step_once(token)
        self.assert_replay(controller)

    def test_running_or_foreign_token_cannot_mutate(self):
        controller = SchedulerController()
        token = controller.pause()
        controller.resume(token)
        before = controller.checkpoint()
        for supplied in (token, SchedulerController().pause()):
            with self.assertRaises(ValueError):
                controller.tune(supplied, {'physics': {'brake_deceleration': 4}})
        self.assertEqual(controller.checkpoint(), before)
