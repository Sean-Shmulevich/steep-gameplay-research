import json
from pathlib import Path
import unittest
from reference.skeleton_link_traversal import plan_skeleton_link_traversal as plan


class SkeletonLinkTraversalTests(unittest.TestCase):
    def test_original_instruction_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/skeleton_link_traversal_validation.json').read_text())
        self.assertEqual(receipt['cases'], 108)
        self.assertFalse(receipt['game_process'])
        for sample in receipt['samples']:
            with self.subTest(inputs=sample['inputs']):
                self.assertEqual(plan(**sample['inputs']), sample['result'])

    def test_cache_is_last_selected_not_global(self):
        result = plan([7, 9, 7], [False, False, True], 65535, 255)
        self.assertEqual([e['selector'] for e in result['events']
                          if e['event'] == 'provider'], [7, 9, 7])
        self.assertEqual([e['event'] for e in result['events'][:2]],
                         ['provider', 'resolve'])
        filtered = plan([7, 9, 7], [True, True, True], 7, 255)
        self.assertEqual([e['index'] for e in filtered['events']
                          if e['event'] == 'provider'], [0])
        self.assertEqual(filtered['pending'], 255)

    def test_sentinel_is_not_proof_of_initialized_transform(self):
        result = plan([65535, 7, 65535], [True]*3, 65535, 3)
        targets = [e for e in result['events'] if e['event'] == 'target']
        self.assertEqual([e['provider_initialized'] for e in targets],
                         [False, True, True])
        self.assertEqual(result['pending'], 2)
        self.assertEqual(plan([], [], 65535, 255), dict(events=[], pending=254))

    def test_authored_input_guards(self):
        for args in [([7], [], 7, 0), ([True], [True], 7, 0),
                     ([7], [1], 7, 0), ([], [], 65536, 0),
                     ([], [], 7, -1)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                plan(*args)
