import json
from pathlib import Path
import unittest
from reference.animation_capacity import plan_capacity_change


class CapacityTests(unittest.TestCase):
    def test_original_capacity_helper(self):
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/animation_capacity_validation.json').read_text())
        for sample in receipt['samples']:
            self.assertEqual(plan_capacity_change(**sample['inputs']),sample['result'])
