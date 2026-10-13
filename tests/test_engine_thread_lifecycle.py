import unittest
from engine.thread_lifecycle import (entry_cas, destructor_cas,
                                     destructor_wait_required, destructor_after_wait,
                                     join_entry, join_after_wait)


class ThreadLifecycleTests(unittest.TestCase):
    def test_explicit_join_zero_shortcut_is_not_a_new_wait_receipt(self):
        self.assertEqual(join_entry(0),
                         dict(call_wait_adapter=False, immediate_result=True))
        for state in (1, 2, 3, -1):
            self.assertEqual(join_entry(state),
                             dict(call_wait_adapter=True, immediate_result=None))

    def test_explicit_join_only_clears_after_zero_adapter_result(self):
        self.assertEqual(join_after_wait(2, 0),
                         dict(state=0, exchange_to_zero=True, result=True))
        for result in (1, 4, -1):
            self.assertEqual(join_after_wait(2, result),
                             dict(state=2, exchange_to_zero=False, result=False))

    def test_destructor_wins_before_entry(self):
        state = destructor_cas(1)['state']
        self.assertEqual(entry_cas(state), dict(state=3, enter_body=False))
        self.assertTrue(destructor_wait_required(state))

    def test_entry_wins_and_destructor_does_not_cancel_body(self):
        entered = entry_cas(1)
        self.assertTrue(entered['enter_body'])
        state = destructor_cas(entered['state'])['state']
        self.assertEqual(state, 2)
        self.assertTrue(destructor_wait_required(state))

    def test_wait_uses_later_observation_and_zero_result_branch(self):
        self.assertEqual(destructor_cas(1)['state'], 3)
        self.assertFalse(destructor_wait_required(0))
        for result in (1, 4, -1):
            self.assertEqual(destructor_after_wait(2, result),
                             dict(state=2, exchange_to_zero=False))
        self.assertEqual(destructor_after_wait(3, 0),
                         dict(state=0, exchange_to_zero=True))

    def test_noncanonical_states_are_not_reinterpreted(self):
        for state in (0, 3, -1, 100):
            self.assertEqual(entry_cas(state), dict(state=state, enter_body=False))
            self.assertEqual(destructor_cas(state)['state'], state)
        for bad in (True, 1.0, 1 << 31):
            with self.assertRaises(ValueError):
                entry_cas(bad)
