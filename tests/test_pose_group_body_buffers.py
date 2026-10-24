import copy
import struct
import unittest

from engine.pose_body_membership import append_pose_body, remove_pose_body
from engine.pose_group_body_buffers import build_pose_group_body_buffers
from engine.pose_body_feedback import write_pose_body_feedback


def body(token, motion):
    return dict(token=token, group=0, index=0xffffffff, flags16=0,
                metadata_flags52=0, flagsaa=0,
                basis=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                tensor170=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                scalar124=1, motion1a0=[motion, 0, 0], motion1ac=[0, 0, 0])


class GroupBodyBuffersTests(unittest.TestCase):
    def group(self):
        group = dict(token=99, count=0, capacity=4, slots=[None]*4)
        bodies = {token: body(token, token) for token in (10, 20, 30)}
        def no_growth(*args):
            self.fail('Retained capacity should suffice')
        for token in (30, 10, 20):
            append_pose_body(group, bodies[token], grow=no_growth)
        return group, bodies

    def test_append_order_and_swap_removal_reach_writeback(self):
        group, bodies = self.group()
        remove_pose_body(group, bodies[30], bodies=bodies,
                         remove_constraints=lambda *args: None,
                         invalid_index=0xffffffff)
        self.assertEqual(group['slots'][:group['count']], [20, 10])
        self.assertEqual(bodies[20]['index'], 0)
        buffers = build_pose_group_body_buffers(group, bodies=bodies,
                                                scalar=2, vector=[0, 0, -1])
        self.assertEqual(buffers['body_tokens'], [20, 10])
        self.assertEqual(struct.unpack('<4f', buffers['body_state'][0][:16]),
                         (20, 0, -2, 0))
        raw = {token: bytearray(0x200) for token in bodies}
        write_pose_body_feedback(buffers['body_tokens'], bodies=raw,
                                 body_state=list(buffers['body_state'].values()))
        self.assertEqual(struct.unpack_from('<3f', raw[20], 0x1a0), (20, 0, -2))
        self.assertEqual(struct.unpack_from('<3f', raw[10], 0x1a0), (10, 0, -2))
        self.assertEqual(raw[30], bytes(0x200))

    def test_rejects_stale_indices_groups_and_duplicate_slots(self):
        group, original = self.group()
        for field, value in [('index', 1), ('group', 98), ('token', 7)]:
            bodies = copy.deepcopy(original)
            bodies[30][field] = value
            with self.assertRaises(ValueError):
                build_pose_group_body_buffers(group, bodies=bodies,
                                               scalar=1, vector=[0, 0, 0])
        group['slots'][1] = 30
        with self.assertRaises(ValueError):
            build_pose_group_body_buffers(group, bodies=original,
                                           scalar=1, vector=[0, 0, 0])

    def test_empty_group_and_layout_truncation_boundary(self):
        result = build_pose_group_body_buffers(dict(token=1, count=0, slots=[]),
                                              bodies={}, scalar=1, vector=[0, 0, 0])
        self.assertEqual(result, dict(body_tokens=[], body_data={}, body_state={}))
        with self.assertRaises(ValueError):
            build_pose_group_body_buffers(dict(token=1, count=65536, slots=[]),
                                          bodies={}, scalar=1, vector=[0, 0, 0])

    def test_growth_mutated_count_is_detected_not_repaired(self):
        group = dict(token=99, count=0, capacity=0, slots=[None, None])
        item = body(10, 3)
        def growth(g, capacity):
            g['count'] = 1
        append_pose_body(group, item, grow=growth)
        group['slots'][0] = 10
        self.assertEqual(item['index'], 0)
        self.assertEqual(group['slots'], [10, 10])
        with self.assertRaises(ValueError):
            build_pose_group_body_buffers(group, bodies={10: item},
                                          scalar=1, vector=[0, 0, 0])

    def test_membership_indices_select_solver_state_and_writeback(self):
        import json
        from pathlib import Path
        from engine.pose_link_builder_bench import inspect
        from engine.pose_link_solve import solve_pose_link_rows
        group, bodies = self.group()
        first_token, second_token = 10, 30
        document = json.loads((Path(__file__).resolve().parents[1] /
                               'engine/examples/pose_link_builder.json').read_text())
        inputs = document['inputs']
        inputs['first_body']['index1c'] = bodies[first_token]['index']
        inputs['second_body']['index1c'] = bodies[second_token]['index']
        bodies[first_token]['motion1a0'] = inputs['first_body']['motion1a0']
        payload = bytearray.fromhex(inputs['payload_hex'])
        struct.pack_into('<f', payload, 0x38, -2)
        inputs['payload_hex'] = payload.hex()
        built = inspect(document)
        buffers = build_pose_group_body_buffers(group, bodies=bodies,
                                                scalar=0, vector=[0, 0, 0])
        untouched = bytes(buffers['body_state'][0])
        context = bytearray(0x190)
        struct.pack_into('<I', context, 0x38, 12)
        struct.pack_into('<I', context, 0x108, 1)
        struct.pack_into('<I', context, 0x120, 2)
        solve_pose_link_rows(context, base_token=0,
            primary_rows=[bytearray.fromhex(x) for x in built['primary_rows_hex']],
            secondary_rows=[bytearray.fromhex(x) for x in built['secondary_rows_hex']],
            results=[bytearray.fromhex(x) for x in built['result_rows_hex']],
            body_data=buffers['body_data'], body_state=buffers['body_state'])
        self.assertEqual(bytes(buffers['body_state'][0]), untouched)
        raw = {token: bytearray(0x200) for token in bodies}
        write_pose_body_feedback(buffers['body_tokens'], bodies=raw,
                                 body_state=list(buffers['body_state'].values()))
        self.assertEqual(struct.unpack_from('<6f', raw[first_token], 0x1a0),
                         (0, 0, -2, 0, 0, 0))
        self.assertEqual(struct.unpack_from('<3f', raw[second_token], 0x1a0),
                         (30, 0, 0))
