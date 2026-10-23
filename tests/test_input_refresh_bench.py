import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from engine.input_refresh_bench import inspect_timeline

ROOT = Path(__file__).parents[1]


class InputRefreshBenchTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT/'engine/examples/input_refresh_plan.json').read_text())

    def test_cli_matches_api_and_suppression_retains_status(self):
        expected = inspect_timeline(self.plan)
        process = subprocess.run([sys.executable, '-m', 'engine.input_refresh_bench',
            'engine/examples/input_refresh_plan.json'], cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(process.stdout), expected)
        rows = expected['observations']
        self.assertEqual(rows[1]['sample'], [.25, .5, 0, 0])
        self.assertEqual(rows[2]['sample'], [0]*4)
        self.assertEqual(rows[2]['status'], 1)
        self.assertEqual(rows[2]['raw'], [.25, .5, 0, 0])
        self.assertEqual(rows[3]['status'], 0)
        self.assertFalse(expected['sample_generation_established'])

    def test_invalid_boundaries_fail_without_mutating_input(self):
        for key, value in [('processor', 'guessed'), ('cache_masked', 1), ('extra', True)]:
            plan = copy.deepcopy(self.plan)
            plan['events'][1][key] = value
            before = copy.deepcopy(plan)
            with self.assertRaises(ValueError): inspect_timeline(plan)
            self.assertEqual(plan, before)
        plan = copy.deepcopy(self.plan)
        plan['events'][0]['now'] = -1
        with self.assertRaises(ValueError): inspect_timeline(plan)


if __name__ == '__main__': unittest.main()
