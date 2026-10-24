import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from engine.pose_body_integration_bench import inspect

FIXTURE=Path(__file__).resolve().parents[1]/'engine/examples/pose_body_integration.json'


class IntegrationBenchTests(unittest.TestCase):
    def document(self):return json.loads(FIXTURE.read_text())

    def test_secondary_example_preserves_motion_and_input(self):
        d=self.document();original=copy.deepcopy(d);out=inspect(d)
        self.assertEqual(d,original)
        self.assertEqual(out['after']['motion1a0'],out['before']['motion1a0'])
        self.assertEqual(out['after']['motion1ac'],out['before']['motion1ac'])
        self.assertNotEqual(out['after']['basis'],out['before']['basis'])
        self.assertEqual(len(out['trig_calls']),1)
        self.assertEqual(out['after']['translation'][2],28)

    def test_rejects_missing_wrong_and_unused_responses(self):
        for replies in ([],[dict(half_angle=.5,sine=0,cosine=1)]):
            d=self.document();d['inputs']['trig_responses']=replies
            with self.assertRaises(ValueError):inspect(d)
        d=self.document();d['inputs']['trig_responses']*=2
        with self.assertRaises(ValueError):inspect(d)

    def test_direct_integration_and_explicit_sequence(self):
        d=self.document();d['sequence']='body_integration'
        d['inputs']['scalar']=.5;d['inputs']['trig_responses']=[]
        self.assertEqual(inspect(d)['after']['translation'],[11,21.5,32])
        d=self.document();d['inputs']['scalar']=.5
        with self.assertRaises(ValueError):inspect(d)
        d=self.document();del d['provenance']
        with self.assertRaises(ValueError):inspect(d)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'result.json'
            subprocess.run([sys.executable,'-m','engine.pose_body_integration_bench',str(FIXTURE),'--output',str(output)],check=True,cwd=FIXTURE.parents[2],capture_output=True)
            self.assertEqual(json.loads(output.read_text())['after']['translation'][2],28)
