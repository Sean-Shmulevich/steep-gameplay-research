import unittest
from engine.mixed_scheduler import MixedScheduler


class CompletionReleasePhasesTests(unittest.TestCase):
    def test_successor_begin_precedes_predecessor_accounting(self):
        for credit in (False, True):
            with self.subTest(credit=credit):
                parent = dict(id='parent', kind='callback', successors=['child'])
                if credit:
                    parent['credit_recipients'] = ['child']
                model = MixedScheduler([parent, dict(id='child', kind='terminal',
                    credit_gate=credit, credits=0)])
                model.submit('parent')
                token = model.reserve('parent')
                model.execute_callback(token)
                model.finish_dispatch(token)
                trace = model.snapshot()['trace']['records']
                phases = [e for e in trace if e['kind'].startswith('mixed_dependency_begin_')]
                self.assertEqual([e['kind'] for e in phases],
                    ['mixed_dependency_begin_enter', 'mixed_dependency_begin_return'])
                for e in phases:
                    self.assertEqual(e['cause'], 'credit' if credit else 'normal_hold')
                    self.assertEqual(e['owner_state'], 'DONE')
                    self.assertEqual(e['owner_executions'], 0)
                    self.assertEqual(e['owner_outstanding_dispatches'], 1)
                names = [e['kind'] for e in trace]
                self.assertLess(names.index('mixed_dependency_begin_enter'), names.index('mixed_terminal_begin'))
                self.assertLess(names.index('mixed_terminal_begin'), names.index('mixed_dependency_begin_return'))
                self.assertLess(names.index('mixed_dependency_begin_return'), names.index('mixed_finalized'))
                self.assertLess(names.index('mixed_finalized'), names.index('mixed_dispatch_accounting_returned'))

    def test_empty_begin_has_no_outstanding_dispatch_to_drain(self):
        model = MixedScheduler([dict(id='parent', kind='range', receivers=[], successors=['child']),
                                dict(id='child', kind='terminal')])
        model.submit('parent')
        trace = model.snapshot()['trace']['records']
        phases = [e for e in trace if e['kind'].startswith('mixed_dependency_begin_')]
        self.assertEqual(len(phases), 2)
        self.assertTrue(all(e['owner_outstanding_dispatches'] == 0 for e in phases))
        self.assertFalse(any(e['kind'] == 'mixed_dispatch_accounting_returned' for e in trace))
