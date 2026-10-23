import unittest
from engine.scheduler_job_teardown import teardown_trace


class SchedulerJobTeardownTests(unittest.TestCase):
    def test_disabled_wait_does_not_consume_observations(self):
        def forbidden():
            raise AssertionError('disabled wait read state')
            yield
        result = teardown_trace(False, forbidden(), delete_storage=True)
        self.assertTrue(result['completed'])
        self.assertEqual(result['polls'], [])
        self.assertEqual(result['events'], [
            'clear_main_invoker', 'install_base_table',
            'clear_completion_invoker', 'clear_after_invoker',
            'clear_before_invoker', 'request_list_teardown',
            'request_lock_teardown', 'request_storage_free'])

    def test_signed_count_and_state_are_independent(self):
        result = teardown_trace(True, [(0, 1), (2, 0xffffffff), (0, 0xffffffff)])
        self.assertEqual([p['wait'] for p in result['polls']], [True, True, False])
        self.assertEqual(result['polls'][-1]['count_signed'], -1)
        self.assertTrue(result['completed'])
        self.assertNotIn('request_storage_free', result['events'])

    def test_missing_release_never_completes(self):
        for observations in ([], [(1, 0)], [(0, 5), (2, 0)]):
            with self.subTest(observations=observations):
                result = teardown_trace(True, observations)
                self.assertFalse(result['completed'])
                self.assertEqual(result['events'], ['clear_main_invoker', 'install_base_table'])

    def test_stops_reading_after_release(self):
        self.assertEqual(len(teardown_trace(True, [(0, 0), ('invalid', -1)])['polls']), 1)

    def test_rejects_out_of_width_reads(self):
        for pair in ((-1, 0), (0, 0x100000000), (True, 0)):
            with self.assertRaises(ValueError):
                teardown_trace(True, [pair])
