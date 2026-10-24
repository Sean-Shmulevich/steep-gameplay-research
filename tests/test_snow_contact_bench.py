import json
from pathlib import Path
import unittest
from engine.snow_contact_bench import inspect

EXAMPLE=Path(__file__).resolve().parents[1]/'engine/examples/snow_contact_outputs.json'


class ContactBenchTests(unittest.TestCase):
    def test_distinct_consumers_and_no_input_mutation(self):
        doc=json.loads(EXAMPLE.read_text());before=json.dumps(doc)
        r=inspect(doc)
        self.assertEqual(json.dumps(doc),before)
        self.assertEqual(r['impulse_submissions'],[])
        self.assertEqual(len(r['report_state']['records']),1)
        self.assertEqual([b['count'] for b in r['accumulated_buckets']],[1,1])
        self.assertEqual([b['point'] for b in r['finalized_buckets']],[[0,1,0,1],[0,-1,0,1]])
        self.assertEqual(r['record_events'],[dict(record=0,reported=True,groups_changed=[0]),dict(record=1,reported=False,groups_changed=[1])])

    def test_positive_gate_adds_submission_without_rescaling_it(self):
        doc=json.loads(EXAMPLE.read_text());doc['gate_one']=.25
        a=inspect(doc);doc['gate_one']=1;b=inspect(doc)
        self.assertEqual(a['impulse_submissions'],b['impulse_submissions'])
        self.assertEqual(a['impulse_submissions'][0]['impulse'],[.125,0,.375,0])
        self.assertEqual(a['report_state'],b['report_state'])

    def test_explicit_provenance_required(self):
        doc=json.loads(EXAMPLE.read_text());del doc['provenance']
        with self.assertRaises(ValueError):inspect(doc)
