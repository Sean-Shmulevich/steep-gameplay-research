import json
import math
from pathlib import Path
import struct
import unittest
from reference.animation_flat_conversion import convert_flat_results


def flt(bits):
    return struct.unpack('<f', struct.pack('<I', bits))[0]


class FlatConversionTests(unittest.TestCase):
    def test_instruction_receipt(self):
        data = json.loads((Path(__file__).resolve().parents[1] /
                           'native/snow_host/flat_conversion_validation.json').read_text())
        self.assertEqual(data['cases'], 80)
        for row in data['rows']:
            records = [struct.pack('<QQfHBB', i+1, 99, flt(w), 1, 0, 0)
                       for i, w in enumerate(row['weights_bits'])]
            events = []; state = {}
            def evaluate(provider, destination, context):
                self.assertEqual(provider, 99)
                events.append(['evaluate', state['token'], destination])
            result = convert_flat_results(records, flt(row['parent_bits']), None, 'output',
                publish_token=lambda c,t: state.update(token=t), evaluate=evaluate,
                prepare_temporary=lambda t,c: (events.append(['prepare']) or 'temporary'),
                blend=lambda o,t,w: events.append(['blend', w]),
                cleanup=lambda t: events.append(['cleanup']))
            self.assertEqual(len(events), len(row['events']))
            for actual, expected in zip(events, row['events']):
                if actual[0] == 'blend':
                    want = flt(expected[1]); got = actual[1]
                    self.assertTrue(math.isnan(got) if math.isnan(want) else got == want)
                else:
                    self.assertEqual(actual, expected)
            want = flt(row['reported_bits']); got = result['reported_weight']
            self.assertTrue(math.isnan(got) if math.isnan(want) else got == want)
            self.assertEqual(result['success'], row['success'])

    def test_group_refused_before_callbacks(self):
        record = struct.pack('<QQfHBB', 1, 99, 1, 1, 5, 0)
        def forbidden(*args):
            self.fail('unsupported tree must not dispatch')
        with self.assertRaises(ValueError):
            convert_flat_results([record], 1, None, None, publish_token=forbidden,
                evaluate=forbidden, prepare_temporary=forbidden, blend=forbidden, cleanup=forbidden)
