import unittest
from engine.worker_execution_wrapper import execute_worker_wrapper


class WorkerWrapperTests(unittest.TestCase):
    def run_case(self, mode=3, tls_context='tls-worker', scope='scope',
                 body_effect=None, completion_effect=None, diagnostic_mode=2):
        job = dict(mode=mode, diagnostic_scope=scope)
        tls = dict(execution_mode=9, scheduler_context=tls_context)
        queue = dict(change_counter=5, workers=[dict(wake_counter=x) for x in (-1, 0, 1)])
        seen = []
        def body(j):
            seen.append(('body', tls['execution_mode']))
            if body_effect: body_effect(j, tls, queue)
        def complete(j):
            seen.append(('complete', tls['execution_mode']))
            if completion_effect: completion_effect(j, tls, queue)
        result = execute_worker_wrapper(context='explicit-context', job=job, tls=tls,
            queue=queue, body=body, complete=complete,
            before_job=lambda c: seen.append(('before', c)),
            after_job=lambda c: seen.append(('after', c)),
            diagnostic_begin=lambda s: seen.append(('diag_begin', s)),
            diagnostic_end=lambda: seen.append(('diag_end', None)),
            notify_worker=lambda i: seen.append(('notify', i)), diagnostic_mode=diagnostic_mode)
        return result, job, tls, queue, seen

    def test_context_and_mode_restore_precede_completion(self):
        r, j, tls, q, seen = self.run_case()
        self.assertEqual(seen, [('diag_begin', 'scope'), ('before', 'explicit-context'),
            ('body', 3), ('after', 'explicit-context'), ('diag_end', None), ('complete', 9)])
        self.assertFalse(r['queue_changed'])
        self.assertNotIn('worker_notified', [e['phase'] for e in r['events']])

    def test_body_queue_change_is_not_a_completion_notification(self):
        r, *_ = self.run_case(body_effect=lambda j,t,q:q.update(change_counter=6))
        self.assertFalse(r['queue_changed'])

    def test_completion_change_coalesces_and_only_signals_negative_old_counter(self):
        r, j, t, q, seen = self.run_case(completion_effect=lambda j,t,q:q.update(change_counter=6))
        self.assertEqual([w['wake_counter'] for w in q['workers']], [0, 1, 1])
        self.assertEqual([x for x in seen if x[0]=='notify'], [('notify', 0)])
        phases = [e['phase'] for e in r['events']]
        self.assertLess(phases.index('completion_return'), phases.index('worker_notified'))
        self.assertFalse(r['global_drain_proved'])

    def test_sentinel_mutation_controls_restore(self):
        _, _, t, _, seen = self.run_case(body_effect=lambda j,t,q:j.update(mode=255))
        self.assertEqual(t['execution_mode'], 3)  # Native reread skips restore.
        _, _, t, _, seen = self.run_case(mode=255, body_effect=lambda j,t,q:j.update(mode=0))
        self.assertEqual(t['execution_mode'], 255)  # Saved sentinel, not old mode 9.

    def test_context_gate_and_scope_are_distinct(self):
        _, _, _, _, seen = self.run_case(tls_context=None, diagnostic_mode=0,
            body_effect=lambda j,t,q:(t.update(scheduler_context='new'),j.update(diagnostic_scope=None)))
        self.assertNotIn(('before','explicit-context'), seen)
        self.assertIn(('after','explicit-context'), seen)
        self.assertEqual(seen[0], ('diag_begin', None))
        self.assertIn(('diag_end', None), seen)  # Captured scope survives mutation.

    def test_exception_does_not_invent_completion_or_mode_unwind(self):
        job=dict(mode=3);tls=dict(execution_mode=9,scheduler_context=None)
        queue=dict(change_counter=0,workers=[]);seen=[]
        def fail(job):raise RuntimeError('body failure')
        with self.assertRaisesRegex(RuntimeError,'body failure'):
            execute_worker_wrapper(context=None,job=job,tls=tls,queue=queue,body=fail,
                complete=lambda j:seen.append('complete'),before_job=lambda c:None,
                after_job=lambda c:None,diagnostic_begin=lambda s:None,
                diagnostic_end=lambda:None,notify_worker=lambda i:None)
        self.assertEqual(seen,[]);self.assertEqual(tls['execution_mode'],3)
