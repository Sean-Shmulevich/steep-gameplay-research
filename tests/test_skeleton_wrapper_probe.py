import unittest
from engine.examples.skeleton_wrapper_probe import run_probe


class SkeletonWrapperTests(unittest.TestCase):
    def test_primary_and_bypass_both_reach_terminal_but_only_primary_executes(self):
        for field in (-2**31, -1, 0, 1, 2**31-1):
            with self.subTest(field=field):
                result = run_probe(field)
                self.assertEqual(len(result['executed_range_jobs']), 7 if field <= 0 else 0)
                terminal = result['jobs']['UpdateSkeletonEndNode']
                self.assertEqual(terminal['holds'], 0)
                self.assertEqual(terminal['started'], 1)
                for name in ('SkeletonUpdate', 'RagdollAfterCamera', 'SkeletonUpdateInteractions'):
                    self.assertEqual(result['jobs'][name]['started'], 1 if field <= 0 else 0)

    def test_field_is_not_a_boolean_or_unsigned_counter(self):
        for field in (True, 2**31, -2**31-1, 0.0):
            with self.assertRaises(ValueError):
                run_probe(field)
