import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from engine.pose_link_bench import inspect

ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'engine/examples/pose_link_update.json'


class LinkBenchTests(unittest.TestCase):
    def fixture(self):return json.loads(EXAMPLE.read_text())

    def test_reduction_transform_cache_and_preserved_bytes(self):
        d=self.fixture();before=copy.deepcopy(d);r=inspect(d)
        self.assertEqual(d,before);self.assertEqual(r['selected_indices'],[2,1,0,3])
        self.assertEqual([row['cached_word'] for row in r['rows']],[102,101,100,103])
        self.assertEqual(r['rows'][0]['first_transformed_point'],[-3,0,-3])
        self.assertEqual(r['rows'][0]['second_transformed_point'],[7,20,2])
        self.assertTrue(all(row['preserved_tail_hex']=='a5a5a5a5' for row in r['rows']))
        self.assertEqual(len(bytes.fromhex(r['payload_hex'])),288)

    def test_small_group_does_not_require_selector_normal(self):
        d=self.fixture();d['inputs']['records']=d['inputs']['records'][:2]
        d['inputs']['records'][0]['field00']=[0,0,0,0]
        d['inputs']['first_entry_flags']=4
        r=inspect(d)
        self.assertFalse(r['reduction_applied']);self.assertEqual(r['selected_indices'],[0,1])
        self.assertEqual(r['flag_byte'],0xa4)

    def test_group_key_width_and_mixed_group_rejection(self):
        d=self.fixture();d['inputs']['records'][0]['detail']=0x10007
        with self.assertRaises(ValueError):inspect(d)
        d['inputs']['key_width']=16
        self.assertEqual(inspect(d)['group_key'],7)
        d['inputs']['records'][0]['detail']=8
        with self.assertRaises(ValueError):inspect(d)

    def test_guards_and_immutability_on_failure(self):
        for change in ('provenance','count','bytes','nan'):
            d=self.fixture()
            if change=='provenance':d['provenance']='native_proven'
            elif change=='count':d['inputs']['records']=[]
            elif change=='bytes':d['inputs']['previous_payload_hex']='00'
            else:d['inputs']['records'][0]['first_point'][0]=float('inf')
            before=copy.deepcopy(d)
            with self.assertRaises(ValueError):inspect(d)
            self.assertEqual(d,before)

    def test_cli_json_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'result.json'
            subprocess.run([sys.executable,'-m','engine.pose_link_bench',str(EXAMPLE),'--output',str(output)],
                cwd=ROOT,check=True,capture_output=True)
            r=json.loads(output.read_text())
            self.assertEqual(r['active_count'],4)
            self.assertEqual(r['provenance'],'authored_synthetic')
