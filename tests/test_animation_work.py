import json
from pathlib import Path
import unittest
from reference.animation_work import gather_work_transforms


class AnimationWorkTests(unittest.TestCase):
    def test_original_instruction_cases(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/animation_work_validation.json').read_text())
        self.assertEqual(receipt['cases'], 256)
        for case in receipt['samples']:
            got = gather_work_transforms(**case['inputs'])
            self.assertEqual(json.loads(json.dumps(got)), case['result'])

    def test_selected_order_and_duplicates_are_preserved(self):
        records = [([1, 2, 3, 4], [0, 0, 0, 1]),
                   ([5, 6, 7, 8], [0, 0, 1, 0])]
        result = gather_work_transforms(records, [1, 0, 1], None, None, True)
        self.assertEqual([r['position'][0] for r in result], [5, 1, 5])
        self.assertIsNot(result[0], result[2])

    def test_parent_position_fourth_lane_is_not_local_scale(self):
        result = gather_work_transforms([([1, 2, 3, 99], [0, 0, 0, 1])], [0],
                                        [10, 20, 30, 7], [0, 0, 0, 1], False)
        self.assertEqual(result[0]['position'], (11, 22, 33, 7))

    def test_inspection_bounds_reject_invalid_channel(self):
        with self.assertRaises(ValueError):
            gather_work_transforms([], [65535], None, None, True)


class ContextWorkTests(unittest.TestCase):
    def test_original_instruction_cases_with_observed_seeds(self):
        from reference.animation_work import gather_context_work
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/context_work_validation.json').read_text())
        self.assertEqual(receipt['cases'], 192)
        for case in receipt['samples']:
            seeds = iter(case['rsqrt_seeds'])
            result = gather_context_work(**case['inputs'], reciprocal_sqrt=lambda _: next(seeds))
            self.assertEqual(json.loads(json.dumps(result)), case['result'])
            self.assertEqual(list(seeds), [])

    def test_context_scale_applies_to_xyz_and_fourth_lane(self):
        import math
        from reference.animation_work import gather_context_work
        result = gather_context_work([([1, 2, 3, 3], [0, 0, 0, 2])], [0],
                    None, None, True, [10, 20, 30, 2], [0, 0, 0, 1],
                    lambda n: 1/math.sqrt(n))[0]
        self.assertEqual(result['position'], (12, 24, 36, 6))
        self.assertEqual(result['rotation'], (0, 0, 0, 1))

    def test_invalid_zero_rotation_is_adapter_rejection(self):
        from reference.animation_work import gather_context_work
        with self.assertRaises(ValueError):
            gather_context_work([([1, 2, 3, 1], [0, 0, 0, 0])], [0],
                                None, None, True, [0, 0, 0, 1], [0, 0, 0, 1], lambda _: 1)


class RawContextTests(unittest.TestCase):
    def test_original_inverse_helper(self):
        from reference.animation_work import invert_context_transform
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/context_inverse_validation.json').read_text())
        self.assertEqual(receipt['cases'], 280)
        for case in receipt['samples']:
            result = invert_context_transform(**case['inputs'])
            self.assertEqual(json.loads(json.dumps(result)), case['result'])

    def test_original_conversion_chain(self):
        from reference.animation_work import convert_raw_context
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/raw_context_validation.json').read_text())
        self.assertEqual(receipt['cases'], 128)
        for case in receipt['samples']:
            result = convert_raw_context(**case['inputs'],
                        reciprocal_sqrt=lambda _: case['rsqrt_seed'])
            self.assertEqual(json.loads(json.dumps(result)), case['result'])

    def test_raw_fourth_lane_is_masked_and_composed_api_reuses_unit_scale(self):
        import math
        from reference.animation_work import gather_raw_context_work
        args = dict(records=[([12, 24, 36, 3], [0, 0, 0, 1])], indices=[0],
                    parent_position=None, parent_rotation=None, direct=True,
                    basis_rows=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]],
                    reciprocal_sqrt=lambda n: 1/math.sqrt(n))
        a = gather_raw_context_work(**args, position=[10, 20, 30, 99])
        b = gather_raw_context_work(**args, position=[10, 20, 30, -7])
        self.assertEqual(a, b)
        self.assertEqual(a[0]['position'], (2, 4, 6, 3))
