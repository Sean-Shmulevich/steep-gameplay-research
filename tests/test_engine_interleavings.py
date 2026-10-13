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

    def test_external_handlers_rejected(self):
        definitions, policy = self.fixture()
        definitions[0]['handler'] = 'unsafe-replay-side-effect'
        with self.assertRaises(ValueError):explore(definitions,policy,['range'])
