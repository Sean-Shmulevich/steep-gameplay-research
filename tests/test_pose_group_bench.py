import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from engine.pose_group_bench import inspect

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'engine/examples/pose_group_partition.json'


class GroupBenchTests(unittest.TestCase):
    def test_connected_components_and_isolated_destinations(self):
        document=json.loads(EXAMPLE.read_text());before=copy.deepcopy(document)
        result=inspect(document)
        self.assertEqual(document,before)
        self.assertEqual(result['component_count'],1)
        self.assertEqual(result['prepared_destinations'],[9,9,0,0])
        self.assertEqual(result['assigned_destinations'],[9,9,10,100])
        self.assertEqual(result['groups'][9]['slots'][:2],[1,2])
        self.assertEqual(result['groups'][9]['count'],2)
        self.assertEqual(result['bodies'][3]['group'],10)
        self.assertEqual(result['bodies'][4]['group'],100)
        self.assertEqual(result['poses'][30]['group'],9)

    def test_all_eligible_leaves_original_empty_without_destroying_it(self):
        d=json.loads(EXAMPLE.read_text());d['inputs']['links']=[];d['inputs']['poses']=[]
        for body in d['inputs']['bodies']:
            body['flags8']=8;body['first_vector']=[0,0,0]
        result=inspect(d)
        self.assertEqual(result['component_count'],0)
        self.assertTrue(result['original_group_reuse_available'])
        self.assertEqual(result['groups'][9]['count'],0)
        self.assertEqual(result['groups'][10]['count'],4)
        self.assertEqual(result['storage_events'],[])

    def test_exhausted_identity_pool_and_alias_rejected(self):
        d=json.loads(EXAMPLE.read_text());d['inputs']['available_groups']=[]
        with self.assertRaises(ValueError):inspect(d)
        d=json.loads(EXAMPLE.read_text());d['inputs']['special_group']=9
        with self.assertRaises(ValueError):inspect(d)

    def test_cli_writes_reusable_json(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'result.json'
            subprocess.run([sys.executable,'-m','engine.pose_group_bench',str(EXAMPLE),
                            '--output',str(output)],cwd=ROOT,check=True,capture_output=True)
            result=json.loads(output.read_text())
            self.assertEqual(result['assigned_destinations'],[9,9,10,100])
            self.assertEqual(result['provenance'],'authored_synthetic')
