import unittest
from engine.interleavings import explore


class InterleavingTests(unittest.TestCase):
    def fixture(self):
        return ([dict(id='range', kind='range', receivers=[0,1], successors=['end']),
                 dict(id='end', kind='terminal')],
                dict(shared_default=2, worker_slots=[True,True],
                     jobs={'range':dict(category=0,limit=2)}))

    def test_all_small_receiver_orders_complete_with_consistent_accounting(self):
        definitions, policy = self.fixture()
        report = explore(definitions, policy, ['range'])
        self.assertTrue(report['complete'])
        self.assertGreater(report['quiescent_leaves'], 2)
        self.assertEqual(report['blocked_leaves'], 0)
        self.assertEqual(report['violations'], [])
        self.assertEqual(report, explore(definitions, policy, ['range']))

    def test_bounds_are_not_reported_as_exhaustive(self):
        definitions, policy = self.fixture()
        for limits in (dict(max_nodes=1), dict(max_depth=1)):
            report = explore(definitions, policy, ['range'], **limits)
            self.assertFalse(report['complete'])
            self.assertEqual(report['status'], 'bounded')

    def test_affinity_blockage_is_distinct_from_quiescence(self):
        report = explore([dict(id='job',kind='callback')],
            dict(shared_default=1,worker_slots=[True],jobs={
                'job':dict(category=0,limit=1,excluded_mask=1)}), ['job'])
        self.assertTrue(report['complete'])
        self.assertEqual(report['blocked_leaves'],1)
        self.assertEqual(report['quiescent_leaves'],0)
        waiting=report['blocked_examples'][0]['waiting_jobs']
        self.assertEqual(waiting[0]['job'],'job')
        self.assertEqual(waiting[0]['state'],'SCHEDULED')
        self.assertEqual(waiting[0]['eligible_workers'],[])

    def test_external_handlers_rejected(self):
        definitions, policy = self.fixture()
        definitions[0]['handler'] = 'unsafe-replay-side-effect'
        with self.assertRaises(ValueError):explore(definitions,policy,['range'])

    def test_credit_deferred_work_is_blocked_even_without_worker_or_hold(self):
        definitions = [dict(id='root',kind='callback',successors=['child']),
                       dict(id='child',kind='callback',credit_gate=True,credits=0)]
        policy = dict(shared_default=1,worker_slots=[True],jobs={
            n:dict(category=0,limit=1) for n in ('root','child')})
        report = explore(definitions,policy,['root'])
        self.assertTrue(report['complete'])
        self.assertEqual(report['blocked_leaves'],1)
        self.assertEqual(report['quiescent_leaves'],0)
        waiting=report['blocked_examples'][0]['waiting_jobs']
        self.assertEqual([j['job'] for j in waiting],['child'])
        self.assertTrue(waiting[0]['deferred'])
        self.assertEqual(waiting[0]['holds'],0)
        self.assertEqual(waiting[0]['eligible_workers'],[])

    def test_conditional_routes_and_join(self):
        for selected in (False,True):
            definitions = [dict(id='root',kind='callback',successors=['route']),
                dict(id='route',kind='conditional',condition=selected,successors=['r'],secondary=['bypass']),
                dict(id='r',kind='range',receivers=[0],successors=['join']),
                dict(id='bypass',kind='terminal',successors=['join']),dict(id='join',kind='terminal')]
            policy = dict(shared_default=2,worker_slots=[True,True],jobs={
                n:dict(category=0,limit=2) for n in ('root','r')})
            report = explore(definitions,policy,['root'])
            self.assertTrue(report['complete'], report)
            self.assertEqual(report['blocked_leaves'],0)
            self.assertEqual(report['quiescent_leaves'],48 if selected else 2)

    def test_oracle_detects_premature_release(self):
        from unittest.mock import patch
        from engine.mixed_scheduler import MixedScheduler
        class BrokenRelease(MixedScheduler):
            def finish_dispatch(self, token, **kwargs):
                self._normal_release(self._dispatch(token)['job'], 'primary', None)
                return super().finish_dispatch(token, **kwargs)
        definitions,policy = self.fixture()
        with patch('engine.interleavings.MixedScheduler',BrokenRelease):
            report = explore(definitions,policy,['range'])
        self.assertEqual(report['status'],'violation')
        self.assertTrue(any(e['issue']=='dependencies released before worker return'
            for v in report['violations'] for e in v['errors']))

    def test_oracle_detects_leaked_dispatch_count(self):
        from unittest.mock import patch
        from engine.mixed_scheduler import MixedScheduler
        class BrokenAccounting(MixedScheduler):
            def finish_dispatch(self, token, **kwargs):
                name = self._dispatch(token)['job']
                result = super().finish_dispatch(token, **kwargs)
                self._jobs[name]['outstanding_dispatches'] += 1
                return result
        definitions,policy = self.fixture()
        with patch('engine.interleavings.MixedScheduler',BrokenAccounting):
            report = explore(definitions,policy,['range'])
        self.assertEqual(report['status'],'violation')
        self.assertTrue(any(e['issue']=='dispatch/accounting mismatch'
            for v in report['violations'] for e in v['errors']))
