import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from engine.animation_bank_bench import run

ROOT=Path(__file__).resolve().parents[1]


class AnimationBankBenchTests(unittest.TestCase):
    def setUp(self):
        self.document=json.loads((ROOT/'engine/examples/animation_bank_input.json').read_text())

    def test_cli_and_receipt_outputs(self):
        process=subprocess.run([sys.executable,'-m','engine.animation_bank_bench',
            'engine/examples/animation_bank_input.json'],cwd=ROOT,capture_output=True,text=True,check=True)
        result=json.loads(process.stdout)
        self.assertEqual(result, json.loads(json.dumps(run(self.document))))
        receipt=json.loads((ROOT/'native/snow_host/numeric_bank_status_validation.json').read_text())
        for supplied,output in zip(self.document['cases'],result['cases']):
            sample=next(s for s in receipt['samples'] if s['inputs']==supplied['inputs'])
            self.assertEqual(output['result']['channels'],sample['channels'])
            self.assertEqual(output['result']['records'],sample['records'])
            self.assertEqual(output['result']['flags'],sample['destination_flags'])

    def test_recorded_seed_gaps_mismatches_and_extras_rejected(self):
        for modification in ('missing','mismatch','extra'):
            doc=copy.deepcopy(self.document)
            observations=doc['cases'][0]['normalization']
            if modification=='missing':observations.clear()
            elif modification=='mismatch':observations[0]['length']+=1
            else:observations.append(observations[0].copy())
            with self.subTest(modification=modification),self.assertRaises(ValueError):run(doc)

    def test_authored_policy_explicit_and_input_immutable(self):
        doc=copy.deepcopy(self.document)
        for case in doc['cases']:
            case['seed_policy']='authored_exact_sqrt';case['normalization']=[]
        before=copy.deepcopy(doc);result=run(doc)
        self.assertEqual(doc,before)
        self.assertEqual(result['cases'][0]['seed_policy'],'authored_exact_sqrt')
        del doc['cases'][0]['seed_policy']
        with self.assertRaises(ValueError):run(doc)

    def test_complete_wrapper_receipts_through_bench(self):
        receipt=json.loads((ROOT/'native/snow_host/grouped_wrapper_pose_validation.json').read_text())
        self.assertEqual(receipt['cases'],64)
        for sample in receipt['samples']:
            doc=dict(schema='animation-bank-bench-v1',cases=[dict(entry='group_wrapper',
                seed_policy='recorded',inputs=sample['inputs'],
                normalization=[dict(length=n,seed=s) for n,s in zip(sample['lengths'],sample['seeds'])])])
            result=run(doc)['cases'][0]['result']
            self.assertEqual([list(c) for c in result['channels']],sample['channels'])
            self.assertEqual(result['records'],sample['records'])
            self.assertEqual(result['flags'],sample['destination_flags'])
            mask=sample['inputs']['group_mask']
            self.assertEqual([c['group_mask'] for c in result['calls']],
                [65535] if mask==65535 else [1<<i for i in range(3) if mask&(1<<i)])
