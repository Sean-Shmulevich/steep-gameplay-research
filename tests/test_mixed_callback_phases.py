import unittest
from engine.mixed_scheduler import MixedScheduler


def binding(callback):
    return dict(version='synthetic-v1', callback=callback)


class CallbackPhaseTests(unittest.TestCase):
    def test_order_and_bookkeeping_boundary(self):
        seen = []
        def observe(phase):
            def callback(context, receiver):
                self.assertEqual(context, 'context')
                self.assertIsNone(receiver)
                status = scheduler.teardown_wait_status('job')
                self.assertEqual(status['executions'], 1)
                self.assertEqual(status['outstanding_dispatches'], 1)
                self.assertEqual(scheduler.snapshot()['jobs']['end']['terminal_begins'], 0)
                seen.append(phase)
                return 255  # Does not choose a branch or skip the next phase.
            return binding(callback)
        scheduler = MixedScheduler([
            dict(id='job', kind='callback', before_handler='b', handler='m',
                 after_handler='a', successors=['end']),
            dict(id='end', kind='terminal')],
            dict(b=observe('before'), m=observe('main'), a=observe('after')))
        scheduler.submit('job')
        token = scheduler.reserve('job')
        scheduler.execute_callback(token, 'context')
        self.assertEqual(seen, ['before', 'main', 'after'])
        scheduler.finish_dispatch(token)
        snapshot = scheduler.snapshot()
        self.assertEqual(snapshot['jobs']['end']['terminal_begins'], 1)
        events = snapshot['trace']['records']
        after = next(e['sequence'] for e in events if e['kind'] == 'mixed_callback_phase_return' and e['phase'] == 'after')
        finalize = next(e['sequence'] for e in events if e['kind'] == 'mixed_finalize_enter' and e['job'] == 'job')
        self.assertLess(after, finalize)

    def test_failure_does_not_invent_after_or_completion(self):
        seen = []
        def fail(ctx, receiver):
            raise RuntimeError('synthetic failure')
        scheduler = MixedScheduler([dict(id='job', kind='callback', handler='m', after_handler='a')],
            dict(m=binding(fail), a=binding(lambda c, r: seen.append('after'))))
        scheduler.submit('job'); token = scheduler.reserve()
        with self.assertRaisesRegex(RuntimeError, 'synthetic failure'):
            scheduler.execute_callback(token)
        self.assertEqual(seen, [])
        self.assertEqual(scheduler.snapshot()['jobs']['job']['outstanding_dispatches'], 1)
        with self.assertRaises(RuntimeError):
            scheduler.finish_dispatch(token)

    def test_rejects_wrong_job_kind_and_unresolved_binding(self):
        for spec in (dict(id='x', kind='range', after_handler='a'),
                     dict(id='x', kind='callback', before_handler='missing')):
            with self.assertRaises(ValueError):
                MixedScheduler([spec], dict(a=binding(lambda c, r: None)))
