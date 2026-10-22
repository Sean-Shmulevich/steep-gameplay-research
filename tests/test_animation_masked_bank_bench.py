from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from engine.animation_bank_bench import run

ROOT=Path(__file__).resolve().parents[1]


class MaskedBankBenchTests(unittest.TestCase):
    def test_instruction_receipt_through_json_boundary(self):
        r=json.loads((ROOT/'native/snow_host/masked_bank_blend_validation.json').read_text())
        def bank(data,vector):return dict(data=data,profile=r['profile'],flags=0,
            records=[dict(id=7,vector=vector,rotation=[0,0,0,1])])
        for row in r['rows']:
            document=dict(schema='animation-bank-bench-v1',cases=[dict(entry='masked_bytes',seed_policy='recorded',
                inputs=dict(destination=bank([205]*64,[-1]*4),first=bank(r['first'],[1,2,3,4]),
                    second=bank(r['second'],[5,6,7,8]),weight=row['weight'],selector=0,request_mask=row['mask'],
                    weight_mode=row['mode'],uniform_groups=row['uniform_groups'],exclusion_mask=row['exclusion_mask']))])
            before=deepcopy(document);result=run(document)['cases'][0]['result']
            self.assertEqual(document,before)
            for key in ('data','flags','records','ranges'):
                self.assertEqual(result[key],row[dict(data='output',ranges='visits').get(key,key)])

    def test_example_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'result.json'
            completed=subprocess.run([sys.executable,'-m','engine.animation_bank_bench',
                'engine/examples/animation_masked_bank_input.json','--output',str(output)],
                cwd=ROOT,text=True,capture_output=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
            result=json.loads(output.read_text())
            self.assertEqual(len(result['cases']),2)
            self.assertNotEqual(result['cases'][0]['result'],result['cases'][1]['result'])

    def test_invalid_mask_controls_and_missing_key(self):
        original=json.loads((ROOT/'engine/examples/animation_masked_bank_input.json').read_text())
        for key,value in (('weight_mode',2),('weight_mode',True),('uniform_groups',65536)):
            d=deepcopy(original);d['cases'][0]['inputs'][key]=value
            with self.assertRaises(ValueError):run(d)
        d=deepcopy(original);del d['cases'][0]['inputs']['destination']['profile']['descriptors'][0]['key']
        with self.assertRaisesRegex(ValueError,'uint32 keys'):run(d)

    def test_nonidentity_rotation_instruction_receipt(self):
        import struct
        r=json.loads((ROOT/'native/snow_host/masked_bank_rotation_validation.json').read_text())
        self.assertEqual(r['cases'],432)
        for row in r['rows']:
            def bank(data,vector,rotation):return dict(data=list(data),profile=r['profile'],flags=0,
                records=[dict(id=7,vector=vector,rotation=rotation)])
            identity=[0,0,0,1];rotation=row['rotation'];byte=row['byte']
            document=dict(schema='animation-bank-bench-v1',cases=[dict(entry='masked_bytes',seed_policy='recorded',
                normalization=[dict(length=n,seed=s) for n,s in zip(row['lengths'],row['seeds'])],
                inputs=dict(destination=bank(bytes([205])*96,[-1]*4,identity),
                    first=bank(bytes([10])*64+struct.pack('<4f',*identity)+bytes([byte])*16,[1,2,3,4],identity),
                    second=bank(bytes([20])*64+struct.pack('<4f',*rotation)+bytes([byte])*16,[5,6,7,8],rotation),
                    weight=row['weight'],selector=0,request_mask=row['mask'],weight_mode=row['mode'],
                    uniform_groups=row['uniform_groups'],exclusion_mask=row['exclusion_mask']))])
            result=run(document)['cases'][0]['result']
            self.assertEqual(result['data'],row['output'])
            self.assertEqual(result['records'],row['records'])
            self.assertEqual(result['flags'],row['flags'])
            self.assertEqual(result['ranges'],row['visits'])
