import json
from pathlib import Path
import unittest
from reference.animation_handle import invalidate_control_record

class ControlRecordInvalidationTests(unittest.TestCase):
    def test_original_instruction_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/control_record_invalidation_validation.json').read_text())
        self.assertEqual(receipt['cases'], 320)
        for row in receipt['rows']:
            self.assertEqual(invalidate_control_record(**row['inputs']), row['result'])

    def test_positive_count_does_not_preserve_object_pointer(self):
        result = invalidate_control_record(16385, 0xffffffff, 1, 0xffffffff, 9)
        self.assertEqual(result['slot'], [1, 0])
        self.assertEqual(result['record_count'], 9)
        self.assertEqual(result['pointer'], 0)
        self.assertEqual(result['status_word'], 0x7fffffff)
        self.assertEqual(result['target_object_flags'], 0xfff80000)

    def test_absent_index_does_not_touch_supplied_record(self):
        result = invalidate_control_record(0, 123, 1, 0xffffffff, 9)
        self.assertIsNone(result['slot'])
        self.assertFalse(result['invalidated'])
        self.assertEqual(result['pointer'], 1)
        self.assertEqual(result['target_object_flags'], 123)

    def test_null_target_preserves_status(self):
        result = invalidate_control_record(1, 123, 0, 0xffffffff, 9)
        self.assertFalse(result['invalidated'])
        self.assertEqual(result['status_word'], 0xffffffff)

    def test_invalid_inputs(self):
        for index in range(5):
            args = [1, 123, 1, 0xffffffff, 9]
            args[index] = -1
            with self.assertRaises(ValueError):
                invalidate_control_record(*args)
