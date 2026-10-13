"""Synthetic lifecycle cases for the submit flag's destructor relationship."""
import unittest
from engine.mixed_scheduler import MixedScheduler


class SubmissionLifetimeTests(unittest.TestCase):
    def test_repeated_submission_sets_flag_without_second_request(self):
        scheduler = MixedScheduler([dict(id='job', kind='callback')])
        self.assertFalse(scheduler.snapshot()['jobs']['job']['usage'])
        scheduler.submit('job')
        scheduler.submit('job')
        job = scheduler.snapshot()['jobs']['job']
        self.assertTrue(job['usage'])
        self.assertEqual(job['requested'], 1)
        token = scheduler.reserve()
        scheduler.execute_callback(token)
        scheduler.finish_dispatch(token)
        job = scheduler.snapshot()['jobs']['job']
        self.assertEqual(job['state'], 'UNSCHEDULED')
        self.assertTrue(job['usage'])
        self.assertEqual(job['outstanding_dispatches'], 0)

    def test_dependency_begin_does_not_imply_direct_submission_flag(self):
        scheduler = MixedScheduler([
            dict(id='root', kind='callback', successors=['child']),
            dict(id='child', kind='callback')])
        scheduler.submit('root')
        token = scheduler.reserve('root')
        scheduler.execute_callback(token)
        scheduler.finish_dispatch(token)
        child = scheduler.snapshot()['jobs']['child']
        self.assertEqual(child['state'], 'SCHEDULED')
        self.assertFalse(child['usage'])
        requested = child['requested']
        scheduler.submit('child')
        child = scheduler.snapshot()['jobs']['child']
        self.assertTrue(child['usage'])
        self.assertEqual(child['requested'], requested)
