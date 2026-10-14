import unittest
from engine.examples.animation_stage_probe import run_probe


class AnimationStageProbeTests(unittest.TestCase):
    def test_reconvergence_requires_both_branches(self):
        rows = run_probe()['observations']
        self.assertEqual(rows[0]['gather_holds'], 2)
        self.assertEqual(rows[1]['gather_holds'], 1)
        self.assertEqual(rows[1]['gather_started'], 0)

    def test_zero_remaining_does_not_release_gather(self):
        rows = run_probe()['observations']
        claimed = rows[2]
        self.assertEqual(claimed['animation_remaining'], 0)
        self.assertEqual(claimed['animation_executions'], 2)
        self.assertEqual(claimed['gather_holds'], 1)
        for row in rows[2:-1]:
            self.assertEqual(row['gather_started'], 0)
            self.assertEqual(row['gather_holds'], 1)
        self.assertEqual(rows[-1]['gather_holds'], 0)
        self.assertEqual(rows[-1]['gather_started'], rows[-1]['gather_requested'])
        self.assertEqual(rows[-1]['animation_executions'], 0)
