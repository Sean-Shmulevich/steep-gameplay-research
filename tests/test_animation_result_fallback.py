import json
from pathlib import Path
import struct
import unittest
from reference.animation_result_fallback import select_fallback_result, publish_fallback_result


class ResultFallbackTests(unittest.TestCase):
    def test_instruction_receipt_and_publication_order(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/result_fallback_validation.json').read_text())
        self.assertEqual(receipt['cases'], 76)
        for row in receipt['rows']:
            records = [bytes(r) for r in row['records']]
            self.assertEqual(select_fallback_result(records), row['selected'])
            events = []; context = object(); output = object()
            def store(ctx, token):
                self.assertIs(ctx, context); events.append(('store', token))
            def dispatch(provider, out):
                self.assertEqual(provider, 99); self.assertIs(out, output)
                self.assertEqual(events[-1][0], 'store'); events.append(('dispatch', provider))
            selected = publish_fallback_result(records, context, output,
                                               publish_token=store, dispatch=dispatch)
            self.assertEqual(selected, row['selected'])
            self.assertEqual([e[1] for e in events if e[0] == 'store'], row['dispatched_tokens'])

    def test_cycle_is_refused_without_inventing_candidate(self):
        def record(kind, span):
            return struct.pack('<QQfHBB', 0, 0, float('-inf'), span, kind, 0)
        # No weight beats the finite initial minimum; helper returns index zero.
        with self.assertRaisesRegex(ValueError, 'cyclic'):
            select_fallback_result([record(5, 3), record(0, 1), record(6, 1)])

    def test_flat_ties_and_all_nan_keep_initial_index(self):
        def record(weight):
            return struct.pack('<QQfHBB', 0, 0, weight, 1, 0, 0)
        self.assertEqual(select_fallback_result([record(.5), record(.5)]), 0)
        self.assertEqual(select_fallback_result([record(float('nan'))]*2), 0)

    def test_failed_filtered_conversion_publishes_original_candidate(self):
        from reference.animation_result_conversion import convert_result_records
        records = [struct.pack('<QQfHBB', 11, 99, .25, 1, 0, 0)]
        events = []
        def attempt(ctx, filtered, start, count, out, weight, a, b):
            self.assertEqual(filtered, [])
            events.append('attempt'); return 0
        def fallback(ctx, original, out):
            publish_fallback_result(original, ctx, out,
                publish_token=lambda context, token: events.append(token),
                dispatch=lambda provider, output: events.append(provider))
        result = convert_result_records(records, .5, {}, {}, attempt=attempt, fallback=fallback)
        self.assertTrue(result['used_fallback'])
        self.assertEqual(events, ['attempt', 11, 99])
