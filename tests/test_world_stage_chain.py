import copy
import json
from pathlib import Path
import unittest
from engine.world_stage_chain import rebuild_world_stage


class WorldStageChainTests(unittest.TestCase):
    def test_original_instruction_receipt(self):
        p = Path(__file__).resolve().parents[1]/'native/snow_host/world_stage_chain_validation.json'
        receipt = json.loads(p.read_text())
        for row in receipt['rows']:
            self.assertEqual(rebuild_world_stage('seed', row['handles'], receipt['wrappers'], row['initial']), row['result'])

    def test_clear_only_selected_terminals_and_preserve_input(self):
        outgoing = {'seed': ['old'], 'a.end': ['setup-only'], 'b.end': ['keep'], 'else': ['stay']}
        before = copy.deepcopy(outgoing)
        result = rebuild_world_stage('seed', [('a', 0x80000000), ('b', 0x7fffffff)],
                                     {'a': ('a.entry', 'a.end')}, outgoing)
        self.assertEqual(result['tail'], 'a.end')
        self.assertEqual(result['outgoing'], {'seed': ['a.entry'], 'a.end': [], 'b.end': ['keep'], 'else': ['stay']})
        self.assertEqual(outgoing, before)

    def test_duplicate_world_preserves_repeated_clear_and_self_link(self):
        result = rebuild_world_stage('seed', [('a', 0xffffffff)]*2,
                                     {'a': ('a.entry', 'a.end')}, {})
        self.assertEqual(result['eligible_worlds'], ['a', 'a'])
        self.assertEqual(result['cleared'], ['seed', 'a.end', 'a.end'])
        self.assertEqual(result['outgoing']['a.end'], ['a.entry'])

    def test_empty_or_null_world_list_leaves_seed_tail(self):
        for handles in ([], [(None, 0xffffffff)], [('missing', 0)]):
            result = rebuild_world_stage('seed', handles, {}, {'seed': ['old']})
            self.assertEqual(result['tail'], 'seed')
            self.assertEqual(result['outgoing']['seed'], [])

    def test_active_lists_are_outside_topology_only_model(self):
        with self.assertRaises(ValueError):
            rebuild_world_stage('seed', [], {}, {}, lists_active=True)

    def test_invalid_status_and_unresolved_eligible_world(self):
        for status in (True, -1, 2**32):
            with self.assertRaises(ValueError):
                rebuild_world_stage('seed', [('a', status)], {}, {})
        with self.assertRaises(ValueError):
            rebuild_world_stage('seed', [('a', 0x80000000)], {}, {})
