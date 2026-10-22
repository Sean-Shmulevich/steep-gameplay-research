import json
from pathlib import Path
import unittest
from reference.animation_work_storage import plan_work_creation


class StorageTests(unittest.TestCase):
    def test_original_creation_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/work_creation_validation.json').read_text())
        for sample in receipt['samples']:
            self.assertEqual(plan_work_creation(**sample['inputs']),sample['result'])
            self.assertEqual(sample['fault_observed'],sample['result']['action']=='null_write_path')

    def test_inline_capacity_boundary(self):
        self.assertFalse(plan_work_creation(False,True,32)['reserve_requested'])
        self.assertTrue(plan_work_creation(False,True,33)['reserve_requested'])
