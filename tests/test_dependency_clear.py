import copy
import json
from pathlib import Path
import unittest
from engine import alternate_dependencies as a, request_state as r


def fixture(active=True):
    root = r.new_dependency_list(['parent'], ['child']); root['active'] = active
    after = r.new_dependency_list(['child']); after['active'] = True
    return a.new_graph({'parent': r.new_job(holds=1, requested=5, started=4, credits=2),
                        'child': r.new_job(holds=1)},
                      {'root': root, 'after': after, 'leaf': r.new_dependency_list()},
                      {'parent': {'kind': 'ordinary', 'outgoing': 'after'},
                       'child': {'kind': 'ordinary', 'outgoing': 'leaf'}})


class DependencyClearTests(unittest.TestCase):
    def test_default_active_stop_preserves_every_field(self):
        graph = fixture(); before = copy.deepcopy(graph)
        with self.assertRaises(a.ActiveDependencyClear):
            a.clear_dependency_list(graph, 'root')
        self.assertEqual(graph, before)

    def test_explicit_continuation_releases_holds_without_acknowledging_work(self):
        graph = fixture(); before = copy.deepcopy(graph)
        events = a.clear_dependency_list(graph, 'root', continue_after_diagnostic=True)
        self.assertEqual(events[0]['kind'], 'active_clear_diagnostic')
        self.assertEqual(events[-1]['kind'], 'dependency_entries_removed')
        self.assertEqual(graph['lists']['root']['successors'], [])
        self.assertEqual(graph['lists']['root']['credit_recipients'], ['child'])
        self.assertEqual(graph['lists']['after']['successors'], ['child'])
        for name in graph['jobs']:
            self.assertEqual(graph['jobs'][name]['holds'], 0)
            for key in ('requested', 'started', 'credits', 'state', 'deferred'):
                self.assertEqual(graph['jobs'][name][key], before['jobs'][name][key])

    def test_inactive_clear_does_not_release_other_lists(self):
        graph = fixture(False); before = copy.deepcopy(graph)
        events = a.clear_dependency_list(graph, 'root')
        self.assertEqual(len(events), 1)
        self.assertEqual(graph['jobs'], before['jobs'])
        self.assertEqual(graph['lists']['after'], before['lists']['after'])
        self.assertEqual(graph['lists']['root']['successors'], [])

    def test_event_budget_rolls_back_continuation(self):
        graph = fixture(); before = copy.deepcopy(graph)
        with self.assertRaises(ValueError):
            a.clear_dependency_list(graph, 'root', continue_after_diagnostic=True, max_events=1)
        self.assertEqual(graph, before)

    def test_native_clear_receipt(self):
        p = Path(__file__).resolve().parents[1]/'native/snow_host/dependency_clear_validation.json'
        receipt = json.loads(p.read_text())
        for row in receipt['rows']:
            graph = copy.deepcopy(row['before'])
            a.clear_dependency_list(graph, 'root', continue_after_diagnostic=row['continue_after_diagnostic'])
            self.assertEqual(graph, row['result'])
