import unittest
from engine.loading_destruction import (stage_increment, take_staged,
                                       publish_captured, take_pending, stop_poll_passes)


class LoadingDestructionTests(unittest.TestCase):
    def test_staged_work_is_invisible_to_stop_poll(self):
        staged = stage_increment(0)
        self.assertEqual(staged, 1)
        self.assertTrue(stop_poll_passes(0, 0))
        captured = take_staged(staged)
        # The exchange clears staged before its value reaches pending.
        self.assertEqual(captured, dict(staged=0, captured=1))
        self.assertTrue(stop_poll_passes(0, 0))
        published = publish_captured(0, captured['captured'])
        self.assertFalse(stop_poll_passes(published['pending'], 0))

    def test_new_publication_survives_current_batch_capture(self):
        batch = take_pending(3)
        following = publish_captured(batch['pending'], 2)
        self.assertEqual(batch['iterations'], 3)
        self.assertEqual(following['pending'], 2)
        self.assertFalse(stop_poll_passes(0, 1))
        self.assertFalse(stop_poll_passes(following['pending'], 0))
        self.assertEqual(take_pending(following['pending'])['iterations'], 2)

    def test_notification_gate_and_signed_overflow(self):
        self.assertEqual(publish_captured(7, 0), dict(pending=7, notify_worker=False))
        self.assertEqual(stage_increment(2**31-1), -(2**31))
        published = publish_captured(2**31-1, 1)
        self.assertTrue(published['notify_worker'])
        self.assertEqual(take_pending(published['pending'])['iterations'], 0)

    def test_rejects_non_int32_observations(self):
        for value in (True, 0.0, 2**31):
            with self.assertRaises(ValueError):
                take_staged(value)
            with self.assertRaises(ValueError):
                stop_poll_passes(0, value)
