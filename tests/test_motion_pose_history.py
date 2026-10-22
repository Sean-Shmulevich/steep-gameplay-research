import json
from pathlib import Path
import unittest
from engine.motion_pose_history import PoseHistory, advance_pose_history


class MotionPoseHistoryTests(unittest.TestCase):
    def test_original_instruction_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/motion_history_validation.json').read_text())
        self.assertTrue(receipt['passed'])
        self.assertEqual(len(receipt['rows']), 12)
        for row in receipt['rows']:
            with self.subTest(row=row):
                state = PoseHistory(b'a'*32, b'b'*32, row['initial_count'])
                out = advance_pose_history(state, row['source'],
                    b'c'*32 if row['source'] == 'valid' else None)
                self.assertEqual(out.count, row['final_count'])
                self.assertEqual(out.downstream_guard_eligible,
                                 row['downstream_guard_called'])
                self.assertEqual(out.current, b'c'*32 if row['source']=='valid' else state.current)
                self.assertEqual(out.previous, state.current if row['source']=='valid' else state.previous)

    def test_missing_provider_gap_does_not_break_history(self):
        state = PoseHistory(bytes(32), bytes(32), 0)
        state = advance_pose_history(state, 'valid', b'a'*32)
        state = advance_pose_history(state, 'missing_provider')
        self.assertEqual(state.count, 1)
        state = advance_pose_history(state, 'valid', b'b'*32)
        self.assertTrue(state.downstream_guard_eligible)
        self.assertEqual(state.previous, b'a'*32)
        state = advance_pose_history(state, 'missing_key')
        self.assertFalse(state.downstream_guard_eligible)
        state = advance_pose_history(state, 'valid', b'c'*32)
        self.assertEqual(state.count, 1)
        self.assertEqual(state.previous, b'b'*32)

    def test_invalid_api_inputs(self):
        with self.assertRaises(ValueError): PoseHistory(bytes(31), bytes(32), 0)
        with self.assertRaises(ValueError): PoseHistory(bytes(32), bytes(32), 256)
        state = PoseHistory(bytes(32), bytes(32), 0)
        with self.assertRaises(ValueError): advance_pose_history(state, 'valid')
        with self.assertRaises(ValueError): advance_pose_history(state, 'missing_key', bytes(32))
        with self.assertRaises(ValueError): advance_pose_history(state, 'invented')

class MotionEndpointTests(unittest.TestCase):
    def test_original_instruction_endpoints(self):
        import struct
        from engine.motion_pose_history import query_endpoints
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/motion_endpoint_validation.json').read_text())
        self.assertEqual(len(receipt['rows']), 32)
        for row in receipt['rows']:
            state = PoseHistory(bytes.fromhex(row['current_hex']),
                                bytes.fromhex(row['previous_hex']), 2)
            start, end = query_endpoints(state, row['local_point'])
            self.assertEqual(struct.pack('<3f', *start).hex(), row['start_hex'])
            self.assertEqual(struct.pack('<3f', *end).hex(), row['end_hex'])

    def test_translation_and_stationary_history(self):
        import struct
        from engine.motion_pose_history import query_endpoints
        pose = struct.pack('<8f', 1, 2, 3, 0, 0, 0, 0, 1)
        endpoints = query_endpoints(PoseHistory(pose, pose, 0), (4, 5, 6))
        self.assertEqual(endpoints, ((5, 7, 9), (5, 7, 9)))
