import unittest
from engine.mixed_scheduler import MixedScheduler


class MixedTeardownStatusTests(unittest.TestCase):
    def test_callback_return_does_not_finish_dispatch_accounting(self):
        scheduler = MixedScheduler([dict(id='job', kind='callback')])
        self.assertFalse(scheduler.teardown_wait_status('job')['wait_enabled'])
        self.assertTrue(scheduler.submit('job'))
        queued = scheduler.teardown_wait_status('job')
        self.assertTrue(queued['wait_enabled'])
        self.assertTrue(queued['would_wait'])
        self.assertEqual(queued['outstanding_dispatches'], 0)
        token = scheduler.reserve('job')
        scheduler.execute_callback(token)
        returned = scheduler.teardown_wait_status('job')
        self.assertTrue(returned['would_wait'])
        self.assertEqual(returned['outstanding_dispatches'], 1)
        scheduler.finish_dispatch(token)
        drained = scheduler.teardown_wait_status('job')
        self.assertTrue(drained['wait_enabled'])
        self.assertFalse(drained['would_wait'])
        self.assertTrue(scheduler.submit('job'))
        self.assertTrue(scheduler.teardown_wait_status('job')['would_wait'])

    def test_empty_range_still_enables_wait_policy(self):
        scheduler = MixedScheduler([dict(id='empty', kind='range', receivers=[])])
        self.assertFalse(scheduler.submit('empty'))
        status = scheduler.teardown_wait_status('empty')
        self.assertTrue(status['wait_enabled'])
        self.assertFalse(status['would_wait'])
        self.assertEqual(status['outstanding_dispatches'], 0)

    def test_dependency_requested_child_can_advance_without_usage_flag(self):
        scheduler = MixedScheduler([
            dict(id='root', kind='callback', successors=['graphics']),
            dict(id='graphics', kind='callback')])
        for cycle in (1, 2):
            scheduler.submit('root')
            scheduler.run_ready()
            jobs = scheduler.snapshot()['jobs']
            self.assertEqual(jobs['root']['requested'], cycle)
            self.assertEqual(jobs['graphics']['requested'], cycle)
            self.assertTrue(jobs['root']['usage'])
            self.assertFalse(jobs['graphics']['usage'])
            self.assertFalse(scheduler.teardown_wait_status('graphics')['would_wait'])
