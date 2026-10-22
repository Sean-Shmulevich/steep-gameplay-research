import json
from pathlib import Path
import unittest
from reference.animation_context_retirement import plan_context_retirement


class ContextRetirementTests(unittest.TestCase):
    def test_original_retirement_paths(self):
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/context_retirement_validation.json').read_text())
        for sample in receipt['samples']:
            with self.subTest(inputs=sample['inputs']):
                self.assertEqual(plan_context_retirement(**sample['inputs']),sample['result'])

    def test_recycled_slot_is_not_a_reference_count_anymore(self):
        result=plan_context_retirement(references=0,status=0x80000000,
            target_word=0x10054321,backing_present=True,
            slot_index=7,free_head=12)
        self.assertEqual(result['references'],12)
        self.assertEqual(result['free_head'],7)
        self.assertFalse(result['target_attached'])
        self.assertEqual(result['status'],1<<26)
        self.assertEqual(result['target_word'],0x10000000)
        self.assertEqual(result['effects'],['target_service','detach_target',
            'mark_retired','unregister_backing','recycle_slot'])
