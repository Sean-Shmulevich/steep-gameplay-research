import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from engine.animation_workbench import inspect_work

ROOT=Path(__file__).resolve().parents[1]


class AnimationWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.request=json.loads((ROOT/'engine/examples/animation_work_input.json').read_text())
    def test_example_pipeline_and_evidence(self):
        result=inspect_work(self.request)
        self.assertEqual([r['position'] for r in result['transforms']],
                         [(1,2,3,1),(2,4,6,3),(1,2,3,1)])
        self.assertTrue(result['normalization']['numerical_substitute'])
        self.assertEqual(len(result['normalization']['calls']),4)
        self.assertFalse(result['evidence']['pose_published'])
        self.assertFalse(result['evidence']['original_engine_equivalence'])
    def test_supplied_seeds_reproduce_original_receipt(self):
        receipt=json.loads((ROOT/'native/snow_host/context_work_validation.json').read_text())
        case=receipt['samples'][5];request=dict(case['inputs'])
        context=dict(kind='converted',position=request.pop('context_position'),
                     rotation=request.pop('context_rotation'))
        request.update(schema='animation-work-input-v1',context=context,
                       normalization=dict(mode='provided_seeds',seeds=case['rsqrt_seeds']))
        result=inspect_work(request)
        self.assertEqual(json.loads(json.dumps(result['transforms'])),case['result'])
        self.assertFalse(result['normalization']['supplied_seed_provenance_verified'])
    def test_no_implicit_normalization_substitute(self):
        del self.request['normalization']
        with self.assertRaisesRegex(ValueError,'explicit'):inspect_work(self.request)
    def test_missing_and_extra_seeds_rejected(self):
        for seeds in ([1],[1]*5):
            self.request['normalization']=dict(mode='provided_seeds',seeds=seeds)
            with self.assertRaisesRegex(ValueError,'seed count'):inspect_work(self.request)
    def test_no_context_preserves_unormalized_rotation(self):
        del self.request['context'];del self.request['normalization']
        result=inspect_work(self.request)
        self.assertEqual(result['transforms'][0]['rotation'],(0,0,0,2))
        self.assertEqual(result['normalization']['mode'],'not_used')
    def test_cli_json_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'result.json'
            run=subprocess.run([sys.executable,'-m','engine.animation_workbench',
                'engine/examples/animation_work_input.json','--output',str(output)],
                cwd=ROOT,capture_output=True,text=True,timeout=10)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(json.loads(output.read_text())['schema'],'animation-work-output-v1')
            bad=Path(folder)/'bad.json';bad.write_text('{"schema":NaN}')
            run=subprocess.run([sys.executable,'-m','engine.animation_workbench',str(bad)],
                cwd=ROOT,capture_output=True,text=True,timeout=10)
            self.assertEqual(run.returncode,2)
            self.assertFalse(json.loads(run.stderr)['ok'])
