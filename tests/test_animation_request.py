import json
from pathlib import Path
import unittest
from reference.animation_request import arbitrate_request


def next_request(result, scalar, context):
    return arbitrate_request(result['work_count'], result['saved_flag'],
                             result['saved_scalar'], result['saved_context'],
                             scalar, context)


class AnimationRequestTests(unittest.TestCase):
    def test_original_instruction_cases(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/animation_request_validation.json').read_text())
        self.assertEqual(receipt['cases'], 504)
        for case in receipt['samples']:
            self.assertEqual(arbitrate_request(**case['inputs']), case['result'])

    def test_defer_bypass_then_consume_once(self):
        first = arbitrate_request(3, 0, 0, 0, 0x3f000000, 22)
        self.assertEqual(first['action'], 'deferred')
        second = next_request(first, 0x3e800000, 11)
        self.assertEqual(second['work_count'], 0)
        self.assertEqual(second['effective_context'], 11)
        self.assertEqual(second['saved_context'], 22)
        third = next_request(second, 0x80000000, 0)
        self.assertTrue(third['consumed_saved'])
        self.assertEqual(third['effective_scalar'], 0x3f000000)
        self.assertEqual(third['effective_context'], 22)
        fourth = next_request(third, 0, 0)
        self.assertFalse(fourth['consumed_saved'])
        self.assertEqual(fourth['effective_context'], 0)

    def test_zero_with_context_and_nan_do_not_consume_saved(self):
        for scalar, context in ((0, 11), (0x7fc00001, 0), (1, 0)):
            result = arbitrate_request(1, 255, 0x3f000000, 22, scalar, context)
            self.assertFalse(result['consumed_saved'])
            self.assertEqual(result['saved_flag'], 255)
            self.assertEqual(result['work_count'], 0)

    def test_empty_work_does_not_create_saved_request(self):
        result = arbitrate_request(0, 0, 0, 0, 0x3f000000, 22)
        self.assertEqual(result['action'], 'continue_evaluation')
        self.assertEqual(result['saved_flag'], 0)
