import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from engine.animation_workbench import inspect_work
ROOT=Path(__file__).resolve().parents[1]


def request_for(sample):
    args=copy.deepcopy(sample['inputs'])
    context=None
    if 'basis_rows' in args:
        context=dict(basis_rows=args.pop('basis_rows'),position=args.pop('context_position'))
    return dict(schema='animation-update-input-v1',**args,context=context,
        numerics=dict(rsqrt='provided_seeds',seeds=sample['rsqrt_seeds'],trig='host_math_substitute'))


class UpdateWorkbenchTests(unittest.TestCase):
    def test_both_instruction_receipts(self):
        for name in ('work_update','context_update'):
            receipt=json.loads((ROOT/f'native/snow_host/{name}_validation.json').read_text())
            for sample in receipt['samples']:
                output=inspect_work(request_for(sample))
                self.assertEqual(json.loads(json.dumps(output['result'])),sample['result'])
                self.assertFalse(any(output['evidence'].values()))

    def test_rejects_ambiguous_numerics_and_mode(self):
        sample=json.loads((ROOT/'native/snow_host/context_update_validation.json').read_text())['samples'][1]
        base=request_for(sample)
        for edit in ({'numerics':{}},{'direct':not base['direct']},{'saved_flag':256}):
            with self.assertRaises(ValueError):inspect_work(dict(base,**edit))
        request=copy.deepcopy(base);request['numerics']['seeds'] += [1.]
        with self.assertRaisesRegex(ValueError,'unused'):inspect_work(request)

    def test_cli_example(self):
        process=subprocess.run([sys.executable,'-m','engine.animation_workbench',
            'engine/examples/animation_update_input.json'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(process.returncode,0,process.stderr)
        output=json.loads(process.stdout)
        self.assertEqual(output['result']['records'][0][0][0],2.)
        self.assertFalse(output['evidence']['deferred_evaluator_executed'])
