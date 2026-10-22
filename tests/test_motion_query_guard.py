import json
from pathlib import Path
import unittest
from engine.motion_query_guard import evaluate_guard


class MotionQueryGuardTests(unittest.TestCase):
    def test_original_instruction_matrix(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/motion_guard_validation.json').read_text())
        self.assertEqual(r['cases'], 400)
        for row in r['rows']:
            got = evaluate_guard(row['bypass'], row['parent_state'],
                                 row['child_state'], row['initial_out'])
            self.assertEqual(got.return_value, bool(row['return_value']))
            self.assertEqual(got.output_byte, row['output'])

    def test_preserved_output_is_not_complement_of_return(self):
        result = evaluate_guard(0, 1, 0, 255)
        self.assertTrue(result.return_value)
        self.assertEqual(result.output_byte, 255)
        self.assertEqual(evaluate_guard(0, 0, 4, 255).output_byte, 1)

    def test_validation(self):
        for values in [(-1,0,0,0),(0,2**32,0,0),(0,0,0,256),(True,0,0,0)]:
            with self.assertRaises(ValueError): evaluate_guard(*values)
