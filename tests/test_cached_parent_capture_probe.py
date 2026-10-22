import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('cached_parent_capture_probe',
    Path(__file__).resolve().parents[1]/'scripts/cached_parent_capture_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class Client:
    def __init__(self):
        self.calls = []
        self.pose = dict(identity=7, guards_matched=True, context_tag=0,
                         cached_parent=[0, 0, 0, 0, 0, 0, 0, 1],
                         primary_parent=None, current_parent=None,
                         **{key: False for key in probe.FLAGS})

    def request(self, method):
        self.calls.append(method)
        return dict(status='completed', result=copy.deepcopy(
            self.pose if method == 'animation.get_cached_parent' else dict(identity=7)))


class CachedParentCaptureTests(unittest.TestCase):
    def test_read_only_sequence_and_limits(self):
        client = Client()
        result = probe.capture_cached_parent(client, samples=3, interval=0)
        self.assertTrue(result['ok'])
        self.assertEqual(client.calls, ['player.get', 'animation.get_cached_parent', 'player.get'] * 3)
        self.assertEqual(result['summary']['adjacent_same_identity_pairs'], 2)
        for key in ('atomic_snapshot', 'invocation_observed', 'safe_native_call_established', 'animation_writes'):
            self.assertFalse(result['summary'][key])

    def test_invalid_bounds_before_io(self):
        for kwargs in (dict(samples=True), dict(samples=33), dict(interval=float('nan')),
                       dict(interval=float('inf')), dict(interval=True), dict(interval=-1)):
            client = Client()
            with self.assertRaises(ValueError):
                probe.capture_cached_parent(client, **kwargs)
            self.assertEqual(client.calls, [])

    def test_replacement_after_observation_is_rejected(self):
        class Replaced(Client):
            def request(self, method):
                result = super().request(method)
                if len(self.calls) == 3:
                    result['result']['identity'] = 8
                return result
        result = probe.capture_cached_parent(Replaced(), samples=1, interval=0)
        self.assertFalse(result['ok'])
        self.assertEqual(result['summary']['rejected_queries'], 1)

    def test_failure_retained_and_not_bridged(self):
        result = probe.capture_cached_parent(Client(), samples=3, interval=0)
        result['rows'][1]['observation'] = dict(status='failed', result=dict(error='refused'))
        summary = probe.summarize_cached_parent(result)
        self.assertEqual(summary['accepted_identity_brackets'], 2)
        self.assertEqual(summary['adjacent_same_identity_pairs'], 0)
        self.assertEqual(result['rows'][1]['observation']['result']['error'], 'refused')

    def test_changes_do_not_imply_invocation(self):
        result = probe.capture_cached_parent(Client(), samples=2, interval=0)
        pose = result['rows'][1]['observation']['result']
        pose.update(callback_eligible=True, function_present=True, context_tag=2)
        pose['cached_parent'][3] = 1
        summary = probe.summarize_cached_parent(result)
        self.assertEqual(summary['callback_eligible_samples'], 1)
        self.assertEqual(summary['flag_change_counts']['callback_eligible'], 1)
        self.assertEqual(summary['pose_change_counts']['cached_parent'], 1)
        self.assertFalse(summary['invocation_observed'])

    def test_malformed_pose_or_missing_identity_not_accepted(self):
        for update in (dict(identity=None), dict(guards_matched=False),
                       dict(context_tag=True), dict(callback_eligible=1),
                       dict(cached_parent=[0]*7), dict(cached_parent=[float('nan')]*8),
                       dict(primary_present=True), dict(primary_parent=[0]*8)):
            client = Client()
            client.pose.update(update)
            self.assertFalse(probe.capture_cached_parent(client, samples=1, interval=0)['ok'])

    def test_identity_change_or_index_gap_breaks_pair(self):
        for change_identity in (False, True):
            result = probe.capture_cached_parent(Client(), samples=2, interval=0)
            row = result['rows'][1]
            if change_identity:
                for key in ('player', 'observation', 'player_after'):
                    row[key]['result']['identity'] = 8
            else:
                row['index'] = 3
            self.assertEqual(probe.summarize_cached_parent(result)['adjacent_same_identity_pairs'], 0)
