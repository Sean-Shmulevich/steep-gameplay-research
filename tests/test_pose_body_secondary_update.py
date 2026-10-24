import struct
import unittest
from engine.pose_body_secondary_update import apply_pose_secondary_body_state


class SecondaryBodyUpdateTests(unittest.TestCase):
    def test_callback_sees_raw_xyz_and_motion_is_restored(self):
        body = bytearray([0xa5]*0x200)
        previous = bytes(body[0x1a0:0x1b8])
        state = struct.pack('<8I', 0x7fc12345, 0x80000000, 3, 99, 4, 5, 6, 100)
        seen = []
        def update(token, raw, scalar):
            seen.append((token, bytes(raw[0x1a0:0x1b8]), scalar))
            raw[0x70:0x74] = b'pose'
            raw[0x1a0:0x1b8] = bytes(24)
        apply_pose_secondary_body_state([1], bodies={1:body}, body_state=[state], update_body=update)
        self.assertEqual(seen, [(1, state[:12]+state[16:28], 1.0)])
        self.assertEqual(body[0x1a0:0x1b8], previous)
        self.assertEqual(body[0x70:0x74], b'pose')
        self.assertEqual(body[0x1b8:], bytes([0xa5])*(0x200-0x1b8))

    def test_next_slot_and_state_reload_but_count_is_captured(self):
        tokens = [1, 2]
        bodies = {i:bytearray([i]*0x200) for i in (1,2,3)}
        states = [bytearray(32), bytearray(32)]
        seen = []
        def update(token, raw, scalar):
            seen.append((token, raw[0x1a0]))
            if token == 1:
                tokens[1] = 3
                tokens.append(2)
                states[1][:] = bytes([7]*32)
        apply_pose_secondary_body_state(tokens, bodies=bodies, body_state=states, update_body=update)
        self.assertEqual(seen, [(1,0), (3,7)])
        self.assertEqual(bodies[2], bytes([2]*0x200))
        self.assertEqual(bodies[3], bytes([3]*0x200))

    def test_repeated_body_restores_before_each_call(self):
        body = bytearray([9]*0x200)
        seen = []
        apply_pose_secondary_body_state([1,1], bodies={1:body},
            body_state=[bytes([2]*32),bytes([3]*32)],
            update_body=lambda token,raw,scalar:seen.append(raw[0x1a0]))
        self.assertEqual(seen, [2,3])
        self.assertEqual(body, bytes([9]*0x200))

    def test_service_exception_has_no_invented_rollback(self):
        body = bytearray([9]*0x200)
        def fail(*args):
            raise RuntimeError('service failed')
        with self.assertRaises(RuntimeError):
            apply_pose_secondary_body_state([1], bodies={1:body},
                body_state=[bytes(32)], update_body=fail)
        self.assertEqual(body[0x1a0:0x1b8], bytes(24))
