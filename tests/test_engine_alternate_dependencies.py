import copy
import json
import unittest

from engine import alternate_dependencies as a
from engine import request_state as r


def active(successors=(), credit_recipients=()):
    result = r.new_dependency_list(successors, credit_recipients)
    result['active'] = True
    return result


def join_graph():
    return a.new_graph(
        {'join': r.new_job(holds=2, requested=7, started=6, credit_gate=True, credits=3),
         'child': r.new_job(holds=1, requested=2, started=1)},
        {'selected': active(['join']), 'unselected': active(['join']),
         'after_join': active(['child']), 'leaf': active()},
        {'join': {'kind': 'ordinary', 'outgoing': 'after_join'},
         'child': {'kind': 'ordinary', 'outgoing': 'leaf'}})


class AlternateDependencyTests(unittest.TestCase):
    def test_alternate_then_normal_shared_join_can_begin(self):
        graph = join_graph()
        events = a.release_alternate(graph, 'unselected')
        self.assertEqual(graph['jobs']['join']['holds'], 1)
        self.assertFalse(any(e['kind'] == 'alternate_callback' for e in events))
        effects = r.release_normal(graph['lists']['selected'], graph['jobs'])
        self.assertEqual(effects[0]['kind'], 'invoke_begin')
        self.assertEqual(graph['jobs']['join']['credits'], 2)
        self.assertTrue(graph['lists']['after_join']['active'])
        self.assertEqual(graph['jobs']['child']['holds'], 1)

    def test_normal_then_alternate_does_not_invent_begin_at_shared_join(self):
        graph = join_graph()
        self.assertEqual(r.release_normal(graph['lists']['selected'], graph['jobs']), [])
        events = a.release_alternate(graph, 'unselected')
        self.assertEqual(graph['jobs']['join']['holds'], 0)
        self.assertEqual(graph['jobs']['child']['holds'], 0)
        self.assertFalse(graph['lists']['after_join']['active'])
        self.assertFalse(any(e['kind'] == 'invoke_begin' for e in events))
        self.assertEqual(graph['jobs']['join']['requested'], 7)
        self.assertEqual(graph['jobs']['join']['started'], 6)
        self.assertEqual(graph['jobs']['join']['credits'], 3)

    def test_active_clear_occurs_after_descendant_callbacks(self):
        graph = join_graph()
        graph['jobs']['join']['holds'] = 1
        events = a.release_alternate(graph, 'unselected')
        cleared = [e['list'] for e in events if e['kind'] == 'alternate_list_cleared']
        self.assertEqual(cleared, ['leaf', 'after_join', 'unselected'])
        self.assertTrue(all(e['source_list_active'] for e in events if e['kind'] == 'alternate_hold_released'))

    def test_nested_conditionals_bypass_both_routes_without_predicate(self):
        jobs = {name: r.new_job(holds=1, requested=4, started=2, credits=8, deferred=True)
                for name in ('branch', 'nested', 'left', 'right', 'other')}
        lists = {'root': active(['branch']), 'p': active(['nested']), 's': active(['other']),
                 'np': active(['left']), 'ns': active(['right']),
                 'left_end': active(), 'right_end': active(), 'other_end': active()}
        bindings = {'branch': {'kind': 'conditional', 'primary': 'p', 'secondary': 's'},
                    'nested': {'kind': 'conditional', 'primary': 'np', 'secondary': 'ns'}}
        bindings.update({name: {'kind': 'ordinary', 'outgoing': name + '_end'} for name in ('left', 'right', 'other')})
        graph = a.new_graph(jobs, lists, bindings)
        before = copy.deepcopy(graph)
        events = a.release_alternate(graph, 'root')
        self.assertTrue(all(job['holds'] == 0 for job in graph['jobs'].values()))
        self.assertTrue(all(not deps['active'] for deps in graph['lists'].values()))
        for name, job in graph['jobs'].items():
            for field in ('requested', 'started', 'credits', 'deferred', 'state', 'credit_gate'):
                self.assertEqual(job[field], before['jobs'][name][field])
        self.assertFalse(any('predicate' in e['kind'] or 'begin' in e['kind'] for e in events))

    def test_added_hold_before_callback_blocks_recursive_release(self):
        graph = join_graph()
        graph['jobs']['join']['holds'] = 1
        self.assertTrue(a.decrement_alternate_hold(graph['jobs']['join']))
        # Explicit synthetic interleaving; add_hold's request increment belongs
        # to the separate normal operation, not the alternate callback.
        r.add_hold(graph['jobs']['join'])
        before = copy.deepcopy(graph)
        events = a.on_alternate_last_hold(graph, 'join')
        self.assertEqual(events[-1]['kind'], 'alternate_callback_blocked')
        self.assertEqual(graph, before)

    def test_credit_recipients_untouched_and_inactive_is_noop(self):
        graph = a.new_graph({'x': r.new_job(credits=5, requested=1, deferred=True)},
                            {'root': active([], ['x']), 'out': active()},
                            {'x': {'kind': 'ordinary', 'outgoing': 'out'}})
        before = copy.deepcopy(graph['jobs'])
        a.release_alternate(graph, 'root')
        self.assertEqual(graph['jobs'], before)
        self.assertTrue(graph['lists']['out']['active'])
        snapshot = copy.deepcopy(graph)
        events = a.release_alternate(graph, 'root')
        self.assertEqual(graph, snapshot)
        self.assertEqual(len(events), 1)
        self.assertFalse(events[0]['active'])

    def test_cycle_unknown_binding_and_aliased_objects_rejected(self):
        with self.assertRaises(ValueError):
            a.new_graph({'x': r.new_job(holds=1)}, {'loop': active(['x'])},
                        {'x': {'kind': 'ordinary', 'outgoing': 'loop'}})
        graph = join_graph()
        graph['bindings']['join']['kind'] = 'unknown_native_subclass'
        with self.assertRaises(ValueError):
            a.release_alternate(graph, 'unselected')
        graph = join_graph()
        graph['jobs']['child'] = graph['jobs']['join']
        with self.assertRaises(ValueError):
            a.release_alternate(graph, 'unselected')

    def test_underflow_and_event_limit_do_not_partially_mutate_graph(self):
        graph = join_graph()
        graph['jobs']['join']['holds'] = 1
        graph['jobs']['child']['holds'] = 0
        before = copy.deepcopy(graph)
        with self.assertRaises(ValueError):
            a.release_alternate(graph, 'unselected')
        self.assertEqual(graph, before)
        graph = join_graph()
        before = copy.deepcopy(graph)
        with self.assertRaises(ValueError):
            a.release_alternate(graph, 'unselected', max_events=1)
        self.assertEqual(graph, before)

    def test_checkpoint_equivalence_and_object_identity_preserved(self):
        graph = join_graph()
        restored = json.loads(json.dumps(graph))
        job_ref, list_ref = graph['jobs']['join'], graph['lists']['unselected']
        self.assertEqual(a.release_alternate(graph, 'unselected'), a.release_alternate(restored, 'unselected'))
        self.assertEqual(graph, restored)
        self.assertIs(graph['jobs']['join'], job_ref)
        self.assertIs(graph['lists']['unselected'], list_ref)

    def test_repeated_entries_remove_distinct_holds(self):
        graph = a.new_graph({'x': r.new_job(holds=2)},
                            {'root': active(['x', 'x']), 'end': active()},
                            {'x': {'kind': 'ordinary', 'outgoing': 'end'}})
        events = a.release_alternate(graph, 'root')
        self.assertEqual(graph['jobs']['x']['holds'], 0)
        self.assertEqual(sum(e['kind'] == 'alternate_callback' for e in events), 1)


if __name__ == '__main__':
    unittest.main()
