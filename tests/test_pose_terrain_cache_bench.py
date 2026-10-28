import copy
import json
from pathlib import Path
import unittest
from engine.pose_terrain_cache_bench import inspect


class TerrainCacheBenchTest(unittest.TestCase):
    def fixture(self):
        return json.loads((Path(__file__).resolve().parents[1]/'engine/examples/pose_terrain_cache.json').read_text())

    def test_lifecycle_is_inspectable_without_input_mutation(self):
        source=self.fixture();before=copy.deepcopy(source)
        result=inspect(source)
        self.assertEqual(source,before)
        self.assertEqual([s['generated_count'] for s in result['steps']],[1,0,1])
        self.assertEqual([s['cache_count'] for s in result['steps']],[1,0,1])
        self.assertEqual([s['recycled_count'] for s in result['steps']],[0,1,0])
        self.assertEqual(result['steps'][0]['groups'][0]['payload'],1)
        self.assertEqual(result['steps'][2]['groups'][0]['payload'],1)
        self.assertEqual(len(bytes.fromhex(result['final_state']['output_hex'])),24000)

    def test_snapshot_continuation_matches_one_run(self):
        source=self.fixture();full=inspect(source)
        first=copy.deepcopy(source);first['steps']=first['steps'][:2]
        checkpoint=inspect(first)['final_state']
        remainder=copy.deepcopy(source);remainder['initial_state']=checkpoint
        remainder['steps']=remainder['steps'][2:]
        self.assertEqual(inspect(remainder)['final_state'],full['final_state'])

    def test_reverse_order_and_key_width(self):
        source=self.fixture();source['pair'].update(order='box_terrain',key_width=16)
        result=inspect(source)
        self.assertEqual([s['generated_count'] for s in result['steps']],[1,0,1])
        self.assertEqual(result['final_state']['cache']['count'],1)

    def test_missing_storage_is_not_fabricated(self):
        source=self.fixture();source['initial_state']['payloads']={}
        with self.assertRaisesRegex(ValueError,'lacks payload'):inspect(source)
        source=self.fixture();source['initial_state']['recycled']['count']=0
        with self.assertRaisesRegex(ValueError,'Recycler exhausted'):inspect(source)
        source=self.fixture();source['steps'][0]['capacity']=128
        with self.assertRaisesRegex(ValueError,'capacity500'):inspect(source)
