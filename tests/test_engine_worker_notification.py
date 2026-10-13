import unittest

from engine.worker_notification import idle_transition, notify_transition


class WorkerNotificationTests(unittest.TestCase):
    def test_notify_before_idle_retains_one_retry(self):
        state = notify_transition(0)
        for _ in range(20):
            self.assertFalse(state['call_notify_adapter'])
            state = notify_transition(state['counter'])
        retry = idle_transition(state['counter'])
        self.assertEqual(retry, dict(counter=0, call_wait_adapter=False))
        self.assertEqual(idle_transition(retry['counter']),
                         dict(counter=-1, call_wait_adapter=True))

    def test_notify_after_idle_requests_event_even_before_wait_call(self):
        parked = idle_transition(0)
        self.assertTrue(parked['call_wait_adapter'])
        notification = notify_transition(parked['counter'])
        self.assertEqual(notification, dict(counter=0, call_notify_adapter=True))
        # This tests the decision only. Whether an early signal is retained is
        # an unresolved property of the protected native event implementation.
        self.assertEqual(notify_transition(notification['counter']),
                         dict(counter=1, call_notify_adapter=False))

    def test_instruction_overflow_and_noncanonical_values(self):
        self.assertEqual(idle_transition(-(2**31)),
                         dict(counter=2**31-1, call_wait_adapter=False))
        self.assertEqual(notify_transition(2**31-1),
                         dict(counter=-(2**31), call_notify_adapter=False))
        self.assertEqual(notify_transition(-2),
                         dict(counter=-1, call_notify_adapter=True))

    def test_rejects_values_without_int32_representation(self):
        for value in (True, 0.0, None, 2**31, -(2**31)-1):
            for transition in (idle_transition, notify_transition):
                with self.subTest(value=value, transition=transition.__name__):
                    with self.assertRaises(ValueError):
                        transition(value)
