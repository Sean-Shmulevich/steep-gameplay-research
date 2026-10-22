import json
import math
from pathlib import Path
import unittest
from reference.animation_work_application import apply_work_records, update_context_free_work, update_context_work


class WorkApplicationTests(unittest.TestCase):
    def test_original_instruction_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/work_application_validation.json').read_text())
        for sample in receipt['samples']:
            with self.subTest(inputs=sample['inputs']):
                seeds = iter(sample['rsqrt_seeds'])
                services = iter(sample['math_services'])
                def trig(name, value):
                    observed = next(services)
                    self.assertEqual((name, value), (observed['name'], observed['input']))
                    return observed['output']
                result = apply_work_records(**sample['inputs'],
                    reciprocal_sqrt=lambda _: next(seeds),
                    acos=lambda x: trig('acos', x), sin=lambda x: trig('sin', x))
                self.assertEqual(json.loads(json.dumps(result)), sample['result'])
                self.assertEqual(list(seeds), [])
                self.assertEqual(list(services), [])

    def test_duplicate_index_reads_previous_write(self):
        result = apply_work_records([((8.,0.,0.,1.),(0.,0.,0.,1.))], [0,0],
            [((0.,0.,0.,1.),(0.,0.,0.,1.))]*2, None, None, True, .5, 1.,
            lambda x: 1/math.sqrt(x), math.acos, math.sin)
        self.assertEqual(result['records'][0][0][0], 2.)

    def test_full_update_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/work_update_validation.json').read_text())
        actions = set()
        for sample in receipt['samples']:
            seeds = iter(sample['rsqrt_seeds'])
            services = iter(sample['math_services'])
            def trig(name, value):
                observed = next(services)
                self.assertEqual((name,value), (observed['name'],observed['input']))
                return observed['output']
            result = update_context_free_work(**sample['inputs'],
                reciprocal_sqrt=lambda _: next(seeds),
                acos=lambda x: trig('acos',x), sin=lambda x: trig('sin',x))
            self.assertEqual(json.loads(json.dumps(result)), sample['result'])
            self.assertEqual(list(seeds), [])
            self.assertEqual(list(services), [])
            actions.add(result['action'])
        self.assertEqual(actions, {'no_bank','expired','count_mismatch','applied'})
    def test_full_context_update_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/context_update_validation.json').read_text())
        actions = set()
        for sample in receipt['samples']:
            seeds = iter(sample['rsqrt_seeds'])
            services = iter(sample['math_services'])
            def trig(name, value):
                observed = next(services)
                self.assertEqual((name,value), (observed['name'],observed['input']))
                return observed['output']
            result = update_context_work(**sample['inputs'],
                reciprocal_sqrt=lambda _: next(seeds),
                acos=lambda x: trig('acos',x), sin=lambda x: trig('sin',x))
            self.assertEqual(json.loads(json.dumps(result)), sample['result'])
            self.assertEqual(list(seeds), [])
            self.assertEqual(list(services), [])
            actions.add(result['action'])
        self.assertEqual(actions, {'no_bank','expired','count_mismatch','applied'})
