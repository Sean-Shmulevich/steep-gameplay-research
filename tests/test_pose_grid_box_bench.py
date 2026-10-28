import json
from pathlib import Path
import unittest
from engine.pose_grid_box_bench import inspect


class GridBenchTest(unittest.TestCase):
    def fixture(self):
        return json.loads((Path(__file__).resolve().parents[1]/'engine/examples/pose_grid_box.json').read_text())

    def test_fixture_filter_effect_and_input_preservation(self):
        doc=self.fixture();before=json.dumps(doc)
        result=inspect(doc)
        self.assertEqual(result['retained_record_count'],15)
        self.assertEqual(json.dumps(doc),before)
        self.assertTrue(all(len(bytes.fromhex(r['record_hex']))==48 for r in result['records']))
        doc['inputs']['filter_enabled']=True
        filtered=inspect(doc)
        self.assertEqual(filtered['retained_record_count'],0)
        self.assertNotEqual(bytes.fromhex(filtered['output_hex']),bytes(16*48))

    def test_zero_capacity_preliminary_success_is_not_a_record(self):
        doc=self.fixture();data=doc['inputs']
        data['capacity']=0;data['preliminary']=True;data['box_frame'][3][2]=-.1
        result=inspect(doc)
        self.assertEqual(result['return_value'],1)
        self.assertEqual(result['records'],[])
        self.assertTrue(result['success_without_record'])

    def test_missing_samples_and_invalid_map_rejected(self):
        doc=self.fixture();doc['inputs']['grid']['samples'].pop()
        with self.assertRaises(ValueError):inspect(doc)
        doc=self.fixture();doc['inputs']['terrain_profiles']['mapb0']=[0]*4
        with self.assertRaises(ValueError):inspect(doc)
