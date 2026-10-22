from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from engine.animation_bank_bench import run

ROOT=Path(__file__).resolve().parents[1]


class ByteBankBenchTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT/'engine/examples/animation_byte_bank_input.json').read_text())

    def test_receipt_output_and_input_immutability(self):
        document=self.fixture();before=deepcopy(document)
        output=run(document);actual=output['cases'][0]['result']
        receipt=json.loads((ROOT/'native/snow_host/regular_bank_rotation_join_validation.json').read_text())
        row=next(r for r in receipt['rows'] if r['mask']==3 and r['weight']==.3 and r['exclusion_mask']==0)
        self.assertEqual(actual,dict(data=row['output'],records=row['records'],flags=row['flags'],ranges=row['visits']))
        self.assertEqual(document,before)
        self.assertEqual(output,run(document))

    def test_seed_mismatch_and_unused_observation_rejected(self):
        for change in ('missing','extra','mismatch'):
            document=self.fixture();observed=document['cases'][0]['normalization']
            if change=='missing':observed.pop()
            elif change=='extra':observed.append(deepcopy(observed[-1]))
            else:observed[0]['length']=123
            with self.assertRaises(ValueError):run(document)

    def test_authored_policy_is_explicit(self):
        document=self.fixture();case=document['cases'][0]
        case['seed_policy']='authored_exact_sqrt';case['normalization']=[]
        result=run(document)['cases'][0]
        self.assertEqual(result['seed_policy'],'authored_exact_sqrt')
        self.assertTrue(result['normalization'])

    def test_command_writes_valid_json(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'result.json'
            result=subprocess.run([sys.executable,'-m','engine.animation_bank_bench',
                'engine/examples/animation_byte_bank_input.json','--output',str(output)],
                cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(output.read_text()),run(self.fixture()))

    def test_invalid_byte_refused(self):
        document=self.fixture();document['cases'][0]['inputs']['first']['data'][0]=256
        with self.assertRaisesRegex(ValueError,'integer bytes'):run(document)
