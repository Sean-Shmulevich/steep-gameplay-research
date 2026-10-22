import json
from pathlib import Path
import unittest
from reference.animation_evaluator import evaluate_work_request


class EvaluatorTests(unittest.TestCase):
    def test_original_complete_evaluator_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/work_evaluator_validation.json').read_text())
        actions=set()
        for sample in receipt['samples']:
            calls=[]
            def resolve(token):
                calls.append(token)
                return None
            def unexpected(_):
                self.fail('context-free gathering must not normalize')
            result=evaluate_work_request(**sample['inputs'],resolve_context=resolve,
                                         reciprocal_sqrt=unexpected)
            self.assertEqual(json.loads(json.dumps(result)),sample['result'])
            self.assertEqual(bool(calls),result['context_resolution_requested'])
            actions.add(result['action'])
        self.assertEqual(actions,{'deferred','cleared','replaced'})

    def test_original_context_evaluator_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/context_evaluator_validation.json').read_text())
        for sample in receipt['samples']:
            seeds=iter(sample['rsqrt_seeds'])
            result=evaluate_work_request(**sample['inputs'],
                resolve_context=lambda _:sample['raw_context'],
                reciprocal_sqrt=lambda _:next(seeds))
            self.assertEqual(json.loads(json.dumps(result)),sample['result'])
            self.assertEqual(list(seeds),[])
