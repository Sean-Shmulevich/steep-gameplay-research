import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from engine.animation_operation_bench import run

ROOT=Path(__file__).resolve().parents[1]


class AnimationOperationBenchTests(unittest.TestCase):
    def setUp(self):
        self.document=json.loads((ROOT/'engine/examples/animation_operation_input.json').read_text())

    def test_cli_example_and_all_mixed_receipts(self):
        process=subprocess.run([sys.executable,'-m','engine.animation_operation_bench',
            'engine/examples/animation_operation_input.json'],cwd=ROOT,capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(process.stdout),json.loads(json.dumps(run(self.document))))
        receipt=json.loads((ROOT/'native/snow_host/ordinary_pose_mixed_validation.json').read_text())
        for sample in receipt['samples']:
            document=dict(schema='animation-operation-bench-v1',cases=[dict(math_policy='recorded',
                inputs=sample['inputs'],services=sample['services'],normalizations=sample['normalizations'])])
            result=run(document)['cases'][0]['result']
            self.assertEqual(json.loads(json.dumps(result)),sample['result'])

    def test_recorded_gaps_mismatches_and_extras_fail(self):
        for field in ('services','normalizations'):
            for fault in ('missing','wrong','extra'):
                document=copy.deepcopy(self.document);rows=document['cases'][0][field]
                self.assertTrue(rows)
                if fault=='missing':rows.clear()
                elif fault=='extra':rows.append(rows[-1].copy())
                else:rows[0]['input' if field=='services' else 'length']+=2
                with self.subTest(field=field,fault=fault),self.assertRaises(ValueError):run(document)

    def test_authored_policy_explicit_and_inputs_unchanged(self):
        document=copy.deepcopy(self.document);case=document['cases'][0]
        case.update(math_policy='authored_host_math',services=[],normalizations=[])
        before=copy.deepcopy(document);result=run(document)
        self.assertEqual(document,before)
        self.assertEqual(result['cases'][0]['math_policy'],'authored_host_math')
        del case['math_policy']
        with self.assertRaises(ValueError):run(document)

    def test_special_route_fails_in_cli_without_output_file(self):
        import tempfile
        document=copy.deepcopy(self.document)
        document['cases'][0]['inputs']['operation'].update(operation_kind=5,special_ready=True)
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'input.json';output=Path(folder)/'result.json'
            source.write_text(json.dumps(document))
            process=subprocess.run([sys.executable,'-m','engine.animation_operation_bench',str(source),
                '--output',str(output)],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(process.returncode,0)
            self.assertIn('special pose service',process.stderr)
            self.assertFalse(output.exists())


    def test_special_entry_matches_full_native_operation_receipts(self):
        receipt=json.loads((ROOT/'native/snow_host/special_pose_operation_validation.json').read_text())
        self.assertEqual(receipt['cases'],96)
        for sample in receipt['samples']:
            document=dict(schema='animation-operation-bench-v1',cases=[dict(entry='special',
                math_policy='recorded',inputs=sample['inputs'],services=sample['services'],
                normalizations=sample['normalizations'])])
            result=run(document)['cases'][0]
            self.assertEqual(result['entry'],'special')
            self.assertEqual(json.loads(json.dumps(result['result'])),sample['result'])
