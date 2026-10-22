import json
from pathlib import Path
import unittest
from engine.examples.postcamera_stage_probe import run_probe, BRANCHES, FOLLOWERS


class PostcameraStageTests(unittest.TestCase):
    def test_two_completion_joins_for_each_delayed_pair(self):
        for branch in BRANCHES:
            for follower in FOLLOWERS:
                with self.subTest(branch=branch, follower=follower):
                    rows = run_probe(branch, follower)['observations']
                    self.assertEqual(list(rows[0]['follower_holds'].values()), [3]*3)
                    for row in rows[1:3]:
                        self.assertEqual(list(row['follower_holds'].values()), [1]*3)
                        self.assertEqual(list(row['follower_started'].values()), [0]*3)
                        self.assertEqual(row['branch_remaining'], 0)
                        self.assertEqual(row['branch_executions'], 1)
                    self.assertEqual(list(rows[3]['follower_holds'].values()), [0]*3)
                    self.assertEqual(rows[4]['join_holds'], 1)
                    self.assertEqual(rows[4]['join_started'], 0)
                    self.assertEqual(rows[5]['join_holds'], 0)

    def test_fixture_matches_original_registration_edges(self):
        root = Path(__file__).resolve().parents[1]
        fixture = json.loads((root/'engine/examples/postcamera_stage_graph.json').read_text())
        receipt = json.loads((root/'native/snow_host/postcamera_dependencies_validation.json').read_text())
        edges = {(j['id'], s) for j in fixture for s in j.get('successors', [])}
        self.assertEqual(edges, {tuple(e) for e in receipt['edges']})
        self.assertEqual(len(edges), 15)
