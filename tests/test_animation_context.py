import json
from pathlib import Path
import unittest
from reference.animation_context import exchange_holder


class AnimationContextTests(unittest.TestCase):
    def test_original_instruction_cases(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/animation_context_validation.json').read_text())
        self.assertEqual(receipt['cases'], 90)
        for case in receipt['samples']:
            self.assertEqual(exchange_holder(**case['inputs']), case['result'])

    def test_alias_is_balanced_without_retiring_live_holder(self):
        self.assertEqual(exchange_holder(1, 1, 0, 0, True),
                         dict(new_count=1, old_count=1, retired=[]))

    def test_replacement_retains_new_and_retires_unreferenced_old(self):
        self.assertEqual(exchange_holder(3, 1, 0, 0),
                         dict(new_count=4, old_count=0, retired=['old']))

    def test_low_status_bits_prevent_retirement_but_visibility_does_not(self):
        self.assertEqual(exchange_holder(1, 1, 0, 1)['retired'], [])
        self.assertEqual(exchange_holder(1, 1, 0, 0x80000000)['retired'], ['old'])
