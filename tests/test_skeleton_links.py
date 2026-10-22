import json
from pathlib import Path
import unittest
from reference.skeleton_links import prune_ineligible_links


class SkeletonLinksTests(unittest.TestCase):
    def test_original_instruction_cases(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/skeleton_links_validation.json').read_text())
        self.assertEqual(receipt['cases'], 484)
        for case in receipt['samples']:
            self.assertEqual(prune_ineligible_links(**case['inputs']), case['result'])

    def test_replacement_is_revisited_and_order_is_unstable(self):
        result = prune_ineligible_links([(0, 'unresolved'), (1, 'worldless'),
                                        (2, 'unresolved'), (3, 'no_skeleton')], 0, True)
        self.assertEqual(result['retained'], [3, 1])
        self.assertEqual(result['calls'], [['replace', 0, 3], ['destroy_last', 3],
                                         ['lookup', 3], ['destroy_last', 2]])

    def test_worldless_parent_keeps_registration_bit(self):
        result = prune_ineligible_links([], 255, False)
        self.assertEqual(result['pending'], 255)
        self.assertEqual(result['calls'], [])
        result = prune_ineligible_links([], 255, True)
        self.assertEqual(result['pending'], 191)
        self.assertEqual(result['calls'], [['unregister', 14]])

    def test_eligible_child_cannot_silently_be_skipped(self):
        with self.assertRaises(ValueError):
            prune_ineligible_links([(0, 'eligible')], 0, True)


class EligibleChildTests(unittest.TestCase):
    def test_original_instruction_cases(self):
        from reference.skeleton_links import plan_eligible_child
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/eligible_child_validation.json').read_text())
        self.assertEqual(receipt['cases'], 768)
        for case in receipt['samples']:
            self.assertEqual(plan_eligible_child(**case['inputs']), case['result'])

    def test_advance_forces_refresh_even_when_initially_clean(self):
        from reference.skeleton_links import plan_eligible_child
        result = plan_eligible_child(2, 8, 1, 255, 0, 0, True, True)
        self.assertEqual(result['calls'], ['prepare_scratch', 'advance_alternate',
                         'lock_child', 'refresh_force1_secondary0', 'unlock_child'])
        self.assertEqual(result['scalar_override'], -1)
        self.assertEqual(result['child_flags'], 247)
        self.assertEqual(result['pending'], 1)

    def test_disabled_advance_can_still_refresh_dirty_child(self):
        from reference.skeleton_links import plan_eligible_child
        result = plan_eligible_child(0, 0, 1, 255, 128, 0, True, False)
        self.assertEqual(result['calls'], ['prepare_child', 'lock_child',
                         'refresh_force1_secondary0', 'unlock_child'])
        self.assertEqual(result['child_flags'], 255)
        self.assertEqual(result['pending'], 0)
