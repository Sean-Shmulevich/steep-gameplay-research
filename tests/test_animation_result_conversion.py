import math
import struct
import unittest
from reference.animation_result_conversion import convert_result_records


def record(weight):
    value = bytearray(24)
    struct.pack_into('<fH', value, 16, weight, 1)
    return bytes(value)


class ResultConversionTests(unittest.TestCase):
    def test_clamp_and_low_byte_fallback_preserve_original(self):
        records = [record(-1), record(0), record(.5), record(float('nan'))]
        for threshold in (float('nan'), -1, -0.0, 0):
            for status in (0, 256, 1, 255, -1):
                with self.subTest(threshold=threshold, status=status):
                    events = []; context = object(); output = {}
                    def attempt(ctx, rows, start, count, out, weight, a, b):
                        self.assertIs(ctx, context); self.assertIs(out, output)
                        self.assertEqual(rows, [records[2]])
                        self.assertEqual((start, count, weight, a, b), (0, 1, 1.0, 0, 0))
                        events.append('attempt'); out['attempted'] = True
                        return status
                    def fallback(ctx, rows, out):
                        self.assertIs(ctx, context); self.assertIs(out, output)
                        self.assertEqual(rows, records)
                        self.assertTrue(out['attempted']); events.append('fallback')
                    result = convert_result_records(records, threshold, context, output,
                                                    attempt=attempt, fallback=fallback)
                    use_fallback = status in (0, 256)
                    self.assertEqual(result['used_fallback'], use_fallback)
                    self.assertEqual(math.copysign(1, result['threshold']), 1)
                    self.assertEqual(events, ['attempt', 'fallback'] if use_fallback else ['attempt'])

    def test_empty_filtered_list_still_attempted(self):
        calls = []
        def attempt(*args):
            calls.append(args); return 1
        def fallback(*args):
            self.fail('successful empty conversion must not fall back')
        for threshold in (.5, float('inf')):
            result = convert_result_records([record(.5)], threshold, None, None,
                                            attempt=attempt, fallback=fallback)
            self.assertEqual(result['filtered_count'], 0)
            self.assertEqual(calls[-1][1:4], ([], 0, 0))
