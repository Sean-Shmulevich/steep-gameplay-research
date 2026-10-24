"""Replay published scalar comparisons; does not launch or validate a live game."""
import json
import math
from pathlib import Path
import struct
import unittest
from engine.markup_snow_vector import snow_vector
from engine.markup_pending import queue_world_scaled_pending


class ProjectionReceiptTests(unittest.TestCase):
    def test_observed_pending_deltas(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/markup_projection_live_validation.json').read_text())
        self.assertEqual(len(receipt['comparisons']), 2)
        for case in receipt['comparisons']:
            with self.subTest(record=case['record']):
                self.assertTrue(case['inputs_equal_at_boundaries'])
                self.assertEqual(case['direction'][3], 0.0)
                self.assertEqual(case['normal'][3], 0.0)
                vector = snow_vector(case['direction'][:3], case['normal'][:3],
                    case['gain'], lambda length2: 1 / math.sqrt(length2)) + [0.0]
                predicted = queue_world_scaled_pending(case['pending_before'],
                    vector, case['interval'])
                self.assertEqual(struct.pack('<4f', *predicted),
                    struct.pack('<4f', *case['pending_after']))
