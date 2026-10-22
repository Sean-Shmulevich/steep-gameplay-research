import json
from pathlib import Path
import unittest
from engine.examples.ragdoll_stage_probe import run_probe, BRANCHES


class RagdollStageTests(unittest.TestCase):
    def test_each_branch_retains_join_until_dispatch_finishes(self):
        for branch in BRANCHES:
            with self.subTest(branch=branch):
                rows = run_probe(branch)['observations']
                self.assertEqual([r['join_holds'] for r in rows], [2, 1, 1, 1, 0, 0])
                for row in rows[2:4]:
                    self.assertEqual(row['delayed_remaining'], 0)
                    self.assertEqual(row['delayed_executions'], 1)
                    self.assertEqual(row['join_started'], 0)
                self.assertEqual(rows[4]['delayed_executions'], 0)

    def test_fixture_matches_native_registration_receipt(self):
        root = Path(__file__).resolve().parents[1]
        fixture = json.loads((root/'engine/examples/ragdoll_stage_graph.json').read_text())
        receipt = json.loads((root/'native/snow_host/ragdoll_dependencies_validation.json').read_text())
        edges = [[j['id'], s] for j in fixture for s in j.get('successors', [])]
        self.assertEqual(edges, receipt['edges'])
        self.assertTrue(all(j['kind'] == 'range' for j in fixture))
