from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from engine.markup_motion_sequence import inspect

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'engine/examples/markup_motion_sequence.json'


class MotionSequenceTests(unittest.TestCase):
    def example(self):
        return json.loads(EXAMPLE.read_text())

    def test_accumulation_skip_consume_and_no_double_application(self):
        data = self.example(); original = deepcopy(data)
        result = inspect(data)
        self.assertEqual(data, original)
        self.assertEqual([e['pending_after'][0] for e in result['events']], [1, 1, 2, 0, 0])
        self.assertEqual([b['linear'] for b in result['bodies']], [[1,0,0], [.5,0,0]])
        self.assertTrue(all(b['angular'] == [0,0,1] for b in result['bodies']))
        self.assertFalse(result['events'][-1]['result']['consumed'])

    def test_suppression_clears_without_velocity_change(self):
        data = self.example(); data['bodies'][0]['flags'] = 8
        result = inspect(data)
        self.assertEqual(result['bodies'][0]['linear'], [0,0,0])
        self.assertEqual(result['bodies'][1]['linear'], [.5,0,0])
        self.assertEqual(result['pending'], [0]*4)

    def test_threshold_retention_and_fourth_lane_dispatch(self):
        data = self.example(); data['events'] = [{'kind':'consume','consumer_reached':True}]
        data['pending_before'] = [1e-5,0,0,0]
        self.assertFalse(inspect(data)['events'][0]['result']['consumed'])
        data['pending_before'] = [0,0,0,1]
        result = inspect(data)
        self.assertTrue(result['events'][0]['result']['consumed'])
        self.assertEqual(result['pending'], [0]*4)
        self.assertTrue(all(b['linear'] == [0]*3 for b in result['bodies']))

    def test_nonfinite_producer_stops_before_consumer(self):
        data = self.example(); p = data['events'][0]['producer']
        p['post_dispatch_state'] = {'current_mode':0,'outer_state':3}
        p['vector_inputs'] = {'current':[0,0,2],'normal':[0,0,1],
            'entity_direction':[1,0,0],'gain':1,'direct_direction':False,'reverse_fallback':False}
        p['rsqrt_seed'] = 'positive_infinity'
        result = inspect(data)
        self.assertEqual(result['status'], 'nonfinite_producer_stopped')
        self.assertEqual(result['events'], [])
        self.assertEqual(result['pending'], [0]*4)

    def test_reachability_is_explicit(self):
        data = self.example(); data['events'][1]['consumer_reached'] = 1
        with self.assertRaises(ValueError): inspect(data)

    def test_cli(self):
        result = json.loads(subprocess.check_output([sys.executable, '-m',
            'engine.markup_motion_sequence', str(EXAMPLE)], cwd=ROOT, text=True))
        self.assertEqual(result['status'], 'computed')
