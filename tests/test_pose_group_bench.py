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


class GroupProcessBenchTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT/'engine/examples/pose_group_process.json').read_text())

    def test_finalization_and_migration_are_connected(self):
        d=self.fixture();before=copy.deepcopy(d);r=inspect(d)
        self.assertEqual(d,before)
        self.assertFalse(r['retirement_requested'])
        self.assertEqual(r['assigned_destinations'],[9,9,10,100])
        c=r['context']
        self.assertEqual(c['groups428']['count'],0)
        self.assertEqual(c['groups418']['slots'][:c['groups418']['count']],[9,100])
        self.assertEqual(c['tracked']['slots'][:c['tracked']['count']],[1,2,3,4])
        self.assertEqual(c['pending_links']['slots'][:c['pending_links']['count']],[20])
        self.assertEqual(r['groups'][100]['index'],1)
        self.assertEqual([e['body'] for e in r['storage_events'] if e['operation']=='body_virtual40_intent'],[1,2,3,4])

    def test_all_eligible_removes_source_and_records_destruction(self):
        d=self.fixture();d['inputs'].update(links=[],poses=[])
        for b in d['inputs']['bodies']:b.update(flags8=8,first_vector=[0,0,0])
        r=inspect(d)
        self.assertTrue(r['retirement_requested'])
        self.assertEqual(r['context']['groups418']['count'],0)
        self.assertEqual(r['destructor_intents'],[dict(group=9,flags=1)])
        self.assertEqual(r['groups'][9]['count'],0)
        self.assertEqual(r['groups'][10]['count'],4)
        # Finalization's tracked list is not silently cleaned by our diagnostic destructor.
        self.assertEqual(r['context']['tracked']['count'],4)
        operations=[e['operation'] for e in r['storage_events']]
        self.assertLess(operations.index('release_temporary'),operations.index('destructor_intent'))

    def test_empty_and_single_branches(self):
        d=self.fixture();d['inputs'].update(bodies=[],links=[],poses=[])
        r=inspect(d)
        self.assertTrue(r['retirement_requested'])
        self.assertIsNone(r['component_count'])
        self.assertNotIn('allocate_temporary',[e['operation'] for e in r['storage_events']])
        d=self.fixture();d['inputs']['bodies']=d['inputs']['bodies'][2:3]
        d['inputs'].update(links=[dict(token=20,first=3,second=3)],
                           poses=[dict(token=30,first=3,second=None)])
        r=inspect(d)
        self.assertTrue(r['retirement_requested'])
        self.assertEqual(r['bodies'][3]['group'],10)
        self.assertEqual(r['links'][20]['index'],0xffffffff)
        self.assertEqual(r['poses'][30]['group'],0)
        self.assertIn(dict(operation='clear_link_intent',link=20),r['storage_events'])
        d['inputs']['bodies'][0]['flags8']=0
        self.assertFalse(inspect(d)['retirement_requested'])

    def test_callback_policy_must_be_explicit(self):
        d=self.fixture();d['inputs']['callback_policy']='native_effects'
        with self.assertRaises(ValueError):inspect(d)

    def test_process_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'result.json'
            subprocess.run([sys.executable,'-m','engine.pose_group_bench',
                str(ROOT/'engine/examples/pose_group_process.json'),'--output',str(output)],
                cwd=ROOT,check=True,capture_output=True)
            result=json.loads(output.read_text())
            self.assertFalse(result['retirement_requested'])
            self.assertEqual(result['context']['groups418']['count'],2)
