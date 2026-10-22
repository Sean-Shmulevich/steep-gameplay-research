import unittest
from scripts.analyze_pending_boundary import analyze


def row(kind, *, pending=0, valid=31, runtime=100, tick=None, request=42):
    values = [10+kind if tick is None else tick, 1, kind, int(kind != 2), 0, request, 0, request, 0, 0,
              valid, runtime, 200, 300, 2, 3, 1]
    values += [pending, 0, 0, 0] + [0]*12 + [.25, .05]
    return ' '.join(map(str, values))


def capture(rows, records=None, dropped=0):
    return f'status=restored\nqpf=1000000\nrecords={len(rows) if records is None else records}\ndropped={dropped}\n' + '\n'.join(rows)


class PendingBoundaryTests(unittest.TestCase):
    def test_transition_and_no_pointer_export(self):
        result = analyze(capture([row(0), row(1, pending=2), row(2, pending=2)]))
        self.assertEqual(result['counts']['matched_requests'], 1)
        self.assertEqual(result['counts']['pending_changed_during_actor_callback'], 1)
        self.assertEqual(result['counts']['pending_changed_before_world_step'], 0)
        self.assertNotIn('runtime', result)

    def test_zero_samples_remain_observations(self):
        result = analyze(capture([row(k) for k in range(3)]))
        self.assertEqual(result['counts']['world_step_entry_pending_nonzero'], 0)
        self.assertTrue(result['limits'])

    def test_missing_and_duplicate_rejected(self):
        for rows in ([row(0), row(2)], [row(0), row(1), row(1), row(2)]):
            self.assertEqual(analyze(capture(rows))['rejected_groups'], {'missing_or_duplicate_boundary': 1})

    def test_identity_and_validity(self):
        for modified, reason in ((row(1, runtime=101), 'object_changed'), (row(1, valid=7), 'invalid_sample')):
            self.assertEqual(analyze(capture([row(0), modified, row(2)]))['rejected_groups'], {reason: 1})

    def test_order_and_record_loss(self):
        result = analyze(capture([row(0), row(1, tick=20), row(2)], records=4, dropped=1))
        self.assertEqual(result['rejected_groups'], {'timestamp_order': 1})
        self.assertFalse(result['recording_complete'])
        self.assertEqual(result['incomplete_records'], 1)

    def test_malformed_and_nonfinite(self):
        for text in (capture(['1 2']), capture([row(0, pending=float('nan'))])):
            with self.assertRaises(ValueError):
                analyze(text)

    def test_next_request_requires_identity_and_adjacency(self):
        first = [row(k, pending=2) for k in range(3)]
        following = [row(k, tick=20+k, request=43) for k in range(3)]
        result = analyze(capture(first + following))
        self.assertEqual(result['next_request_observations']['zero_by_next_actor_entry'], 1)
        for request, runtime in ((44, 100), (43, 999)):
            following = [row(k, tick=20+k, request=request, runtime=runtime) for k in range(3)]
            self.assertEqual(analyze(capture(first + following))['next_request_observations'], {})


class InputWindowTests(unittest.TestCase):
    def qualify(self, events):
        import json
        from scripts.analyze_pending_boundary import qualify_input_window
        recording = capture([row(k, tick=10+k) for k in range(3)] +
                            [row(k, tick=30+k, request=43) for k in range(3)])
        return qualify_input_window(recording, '\n'.join(json.dumps(e) for e in events))

    def event(self, kind, tick, frequency=1000000, released=True):
        return dict(kind=kind, qpc_ticks=tick, qpc_frequency=frequency,
                    all_injected_keys_released=released)

    def test_single_pulse_and_post_release_coverage(self):
        r = self.qualify([self.event('hold_start', 15), self.event('hold_complete', 20)])
        self.assertTrue(r['exactly_one_complete_pulse_covered'])
        self.assertEqual(r['post_release_recorded_seconds'], 12/1000000)

    def test_missing_late_duplicate_or_unreleased_pulse(self):
        start, end = self.event('hold_start', 15), self.event('hold_complete', 20)
        for events in ([start], [start, end, start, end],
                       [start, self.event('hold_complete', 40)],
                       [start, self.event('hold_complete', 20, released=False)],
                       [self.event('hold_start', 1), end]):
            r = self.qualify(events)
            self.assertFalse(r['exactly_one_complete_pulse_covered'])
            self.assertIsNone(r['post_release_recorded_seconds'])

    def test_clock_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            self.qualify([self.event('hold_start', 15, frequency=1)])
