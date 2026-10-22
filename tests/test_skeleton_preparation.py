import json
from pathlib import Path
import unittest
from reference.skeleton_preparation import plan_preparation
from reference.skeleton_links import plan_eligible_child


class SkeletonPreparationTests(unittest.TestCase):
    def test_original_instruction_cases(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/skeleton_preparation_validation.json').read_text())
        self.assertEqual(receipt['cases'], 432)
        for case in receipt['samples']:
            self.assertEqual(plan_preparation(**case['inputs']), case['result'])

    def test_preparation_can_create_pending_without_parent_advance(self):
        prepared = plan_preparation(0xbf800000, False, 8, 3, 0)
        result = plan_eligible_child(0, 0, 0, 0, 0, prepared['pending'], True, False)
        self.assertEqual(prepared['pending'], 1)
        self.assertIn('refresh_force1_secondary0', result['calls'])
        self.assertNotIn('advance_default', result['calls'])

    def test_negative_zero_is_consumed_nan_is_preserved(self):
        self.assertEqual(plan_preparation(0x80000000, False, 0, None, 0)['scalar_bits'],
                         0xbf800000)
        self.assertEqual(plan_preparation(0x7fc00001, False, 0, None, 0)['scalar_bits'],
                         0x7fc00001)

    def test_zero_mask_clears_work_without_setting_pending(self):
        result = plan_preparation(0xbf800000, True, 1, 3, 0xa4)
        self.assertEqual(result['calls'], ['clear_work'])
        self.assertEqual(result['work_count'], 0)
        self.assertTrue(result['counters_cleared'])
        self.assertEqual(result['pending'], 0xa4)
