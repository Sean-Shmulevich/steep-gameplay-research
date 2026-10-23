import copy
import json
import unittest
from engine.scheduler_capture_correlation import correlate_graphics_captures


class CaptureCorrelationTests(unittest.TestCase):
    def envelopes(self):
        base, owner = 0x140000000, 0x300000
        def capture(final):
            summary = dict(kind='summary', record_abi=1 if final else 3, compatible=1,
                configured=1, installed=1, restored=1, drained=1, used=1, dropped=0,
                qpf=1000, owner=hex(owner))
            if final:
                summary['probe'] = 'finalizer'
            state = dict(valid=1, executions=0 if final else 1, outstanding=1,
                         state=2, started=17, requested=17, holds=0, usage=0, selector=0)
            after = dict(state, state=0 if final else 2)
            record = dict(kind='record', index=0, storage=hex(0 if final else owner+0x3b0),
                receiver=hex(owner+0x218 if final else owner),
                caller=hex(base+(0x11e2dff if final else 0x65b223)),
                entry=30 if final else 10, exit=40 if final else 20,
                thread=7, before=state, after=after)
            return dict(session='synthetic-process-generation', image_base=base, rows=[summary, record])
        return capture(False), capture(True)

    def test_matches_and_redacts_identity(self):
        a, b = self.envelopes();r = correlate_graphics_captures(a, b)
        self.assertEqual(r['pair_count'], 1)
        self.assertEqual(r['pairs'][0], dict(request=17, observed_order=True,
            same_thread=True, gap_ticks=10, accounting_matches=True, inside_shared_interval=None))
        self.assertNotIn(a['session'], json.dumps(r))
        self.assertFalse(r['outstanding_decrement_observed'])

    def test_rejects_cross_session_clock_owner_and_binding(self):
        for change in ('session', 'clock', 'owner', 'caller', 'dropped', 'restore'):
            a, b = self.envelopes()
            if change == 'session': b['session'] = 'another'
            if change == 'clock': b['rows'][0]['qpf'] = 999
            if change == 'owner': b['rows'][0]['owner'] = '400000'
            if change == 'caller': b['rows'][1]['caller'] = '1'
            if change == 'dropped': b['rows'][0]['dropped'] = 1
            if change == 'restore': b['rows'][0]['restored'] = 0
            with self.subTest(change=change), self.assertRaises(ValueError):
                correlate_graphics_captures(a, b)

    def test_changed_or_invalid_request_is_not_paired(self):
        for field in ('valid', 'requested'):
            a, b = self.envelopes();a['rows'][1]['after'][field] = 0
            r = correlate_graphics_captures(a, b)
            self.assertEqual(r['pair_count'], 0);self.assertEqual(r['rejected_main'], 1)
            self.assertEqual(r['unmatched_finalizer'], 1)

    def test_duplicate_request_is_ambiguous(self):
        a, b = self.envelopes();a['rows'].append(copy.deepcopy(a['rows'][1]))
        a['rows'][-1]['index'] = 1;a['rows'][0]['used'] = 2
        r = correlate_graphics_captures(a, b)
        self.assertEqual(r['ambiguous_requests'], [17]);self.assertEqual(r['pair_count'], 0)

    def test_overlap_and_changed_accounting_remain_visible(self):
        a, b = self.envelopes();b['rows'][1]['entry'] = 15
        b['rows'][1]['after']['outstanding'] = 0;b['rows'][1]['thread'] = 8
        p = correlate_graphics_captures(a, b)['pairs'][0]
        self.assertFalse(p['observed_order']);self.assertFalse(p['accounting_matches'])
        self.assertFalse(p['same_thread']);self.assertEqual(p['gap_ticks'], -5)

    def test_window_edges_are_unmatched(self):
        a, b = self.envelopes()
        for state in ('before', 'after'):
            b['rows'][1][state].update(started=18, requested=18)
        r = correlate_graphics_captures(a, b)
        self.assertEqual((r['pair_count'], r['unmatched_main'], r['unmatched_finalizer']), (0, 1, 1))

    def test_nonoverlapping_capture_windows_are_explicit(self):
        a, b = self.envelopes()
        for state in ('before', 'after'):
            b['rows'][1][state].update(started=18, requested=18)
        report = correlate_graphics_captures(a, b)
        self.assertFalse(report['observed_capture_windows_overlap'])
        self.assertEqual(report['pair_count'], 0)

    def test_shared_interval_markers_and_boundary_pairs(self):
        a, b = self.envelopes()
        for capture in (a, b):
            capture['rows'][0].update(joint_start_tick=10, joint_end_tick=40)
        report = correlate_graphics_captures(a, b)
        self.assertEqual(report['shared_interval_ticks'], 30)
        self.assertTrue(report['pairs'][0]['inside_shared_interval'])
        for capture in (a, b):
            capture['rows'][0]['joint_end_tick'] = 39
        self.assertFalse(correlate_graphics_captures(a, b)['pairs'][0]['inside_shared_interval'])
        b['rows'][0]['joint_end_tick'] = 40
        with self.assertRaises(ValueError):
            correlate_graphics_captures(a, b)
