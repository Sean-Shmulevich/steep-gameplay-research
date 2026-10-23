import unittest
from engine.mixed_scheduler import MixedScheduler


def binding(callback):
    return dict(version='synthetic-v1', callback=callback)


class ReservationPhaseTests(unittest.TestCase):
    def test_reservation_precedes_body_and_keeps_dispatch_accounted(self):
        seen = []
        def observe(phase):
            def callback(context, receiver):
                self.assertEqual(context, 'ctx')
                self.assertIsNone(receiver)
                job = scheduler.snapshot()['jobs']['job']
                self.assertEqual((job['state'], job['executions'], job['outstanding_dispatches']), ('DONE', 1, 1))
                seen.append(phase)
            return binding(callback)
        scheduler = MixedScheduler([dict(id='job', kind='callback',
            reservation_handler='r', before_handler='b', handler='m', after_handler='a')],
            {name: observe(phase) for name, phase in [('r','reservation'),('b','before'),('m','main'),('a','after')]})
        scheduler.submit('job')
        scheduler.dispatch_next('ctx')
        self.assertEqual(seen, ['reservation', 'before', 'main', 'after'])
        self.assertFalse(scheduler.teardown_wait_status('job')['would_wait'])
        event = next(e for e in scheduler.snapshot()['trace']['records'] if e['kind']=='mixed_callback_reservation_enter')
        self.assertIn('category queue held', event['native_lock_context'])

    def test_failed_reservation_leaves_accounting_and_fault(self):
        def fail(context, receiver):
            raise RuntimeError('reservation failure')
        scheduler = MixedScheduler([dict(id='job', kind='callback', reservation_handler='r')], {'r':binding(fail)})
        scheduler.submit('job')
        with self.assertRaisesRegex(RuntimeError, 'reservation failure'):
            scheduler.reserve('job')
        self.assertEqual(scheduler.snapshot()['jobs']['job']['outstanding_dispatches'], 1)
        with self.assertRaises(RuntimeError):
            scheduler.run_ready()

    def test_rejects_reservation_binding_on_range(self):
        with self.assertRaises(ValueError):
            MixedScheduler([dict(id='range', kind='range', reservation_handler='r')], {'r':binding(lambda c,r:None)})
