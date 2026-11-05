import struct
import unittest

from engine.pose_island_action_tree import (walk_pose_action_tree, wake_action_body,
                                            run_island_action_stage, ACTION_TREE_OFFSET)
from engine.pose_pair_link_worker import PoseFlatMemory

TREE = 0x1000
NODES = 0x2000
ENTRY = 0x3000
BODY = 0x4000
META = 0x5000
HOLDER = 0x6000
CTRL = 0x7000


def make(keys_states):
    """Perfect black tree over sorted keys; entry k has state keys_states[k][1]."""
    n = len(keys_states)
    nodes = bytearray(n * 32)
    regions = {}

    def build(lo, hi, parent=-1):
        if lo >= hi:
            return -1
        mid = (lo + hi) // 2
        left = build(lo, mid, mid)
        right = build(mid + 1, hi, mid)
        struct.pack_into('<iiiBB', nodes, mid * 32, left, right, parent, 0, 0)
        struct.pack_into('<QI', nodes, mid * 32 + 16, ENTRY + mid * 0x20, keys_states[mid][0])
        return mid

    root = build(0, n)
    desc = bytearray(0x20)
    struct.pack_into('<Qii', desc, 0, NODES, n, 0)
    struct.pack_into('<ii', desc, 20, root, -1)
    regions[TREE] = desc
    regions[NODES] = nodes or bytearray(32)
    for k, (_, state) in enumerate(keys_states):
        e = bytearray(0x20)
        struct.pack_into('<QQI', e, 0, 0, BODY + k * 0x200, state)
        regions[ENTRY + k * 0x20] = e
        b = bytearray(0x200)
        struct.pack_into('<Q', b, 0x10, 0x99)
        struct.pack_into('<Q', b, 0x30, META + k * 0x60)
        struct.pack_into('<I', b, 0x28, 0x3f800000)
        regions[BODY + k * 0x200] = b
        m = bytearray(0x60)
        struct.pack_into('<Q', m, 0x20, HOLDER)
        m[0x53] = 0x52
        regions[META + k * 0x60] = m
    h = bytearray(0x40)
    struct.pack_into('<Q', h, 0x20, CTRL)
    regions[HOLDER] = h
    c = bytearray(0x80)
    struct.pack_into('<Q', c, 0x30, 0x5500)
    regions[CTRL] = c
    return PoseFlatMemory(regions)


class ActionTreeWalkTests(unittest.TestCase):
    def services(self, mem, log, on_update=None):
        def update(entry, dt):
            log.append(('update', entry, dt))
            if on_update:
                on_update(entry)
        return dict(update=update,
                    destroy=lambda e, f: log.append(('destroy', e, f)),
                    callback=lambda body: log.append(('callback', body)))

    def test_in_order_by_key_and_callback_after_update(self):
        mem = make([(10, 0), (20, 0), (30, 0)])
        log = []
        walk_pose_action_tree(mem, TREE, 0.5, **self.services(mem, log))
        self.assertEqual([e[1] for e in log if e[0] == 'update'],
                         [ENTRY, ENTRY + 0x20, ENTRY + 0x40])
        self.assertEqual(log[0:2], [('update', ENTRY, 0.5), ('callback', BODY)])

    def test_state_two_retires_then_destroys_and_walk_continues(self):
        mem = make([(1, 2), (2, 0), (3, 2), (4, 2), (5, 0), (6, 2), (7, 2)])
        log = []
        walk_pose_action_tree(mem, TREE, 0.1, **self.services(mem, log))
        self.assertEqual(sum(e[0] == 'update' for e in log), 7)
        destroyed = [e[1] for e in log if e[0] == 'destroy']
        self.assertEqual(destroyed, [ENTRY + k * 0x20 for k in (0, 2, 3, 5, 6)])
        self.assertTrue(all(e[2] == 1 for e in log if e[0] == 'destroy'))
        self.assertEqual(mem.d(TREE + 8), 2)  # active count
        # retirement happens before destroy; a second walk sees only survivors
        log.clear()
        walk_pose_action_tree(mem, TREE, 0.1, **self.services(mem, log))
        self.assertEqual([e[1] for e in log if e[0] == 'update'], [ENTRY + 0x20, ENTRY + 0x80])

    def test_update_can_finish_entry_and_replace_body(self):
        mem = make([(5, 0)])

        def on_update(entry):
            mem.set_d(entry + 0x10, 2)
            mem.set_q(entry + 8, 0xABC)
        log = []
        walk_pose_action_tree(mem, TREE, 0.0, **self.services(mem, log, on_update))
        self.assertEqual(log[1], ('callback', 0xABC))  # body reloaded after update
        self.assertEqual(log[2], ('destroy', ENTRY, 1))
        self.assertEqual(mem.i(TREE + 0x14), -1)

    def test_empty_tree_is_a_no_op(self):
        mem = make([])
        self.assertEqual(walk_pose_action_tree(mem, TREE, 1.0, update=None, destroy=None,
                                               callback=None), [])


class WakeCallbackTests(unittest.TestCase):
    def run_wake(self, mem, body):
        log = []
        done = wake_action_body(mem, body, enter=lambda s: log.append(('enter', s)),
                                leave=lambda s: log.append(('leave', s)),
                                transition=lambda c, b: log.append(('transition', c, b)))
        return done, log

    def test_admitted_wake_resets_quiet_state_inside_sync(self):
        mem = make([(1, 0)])
        done, log = self.run_wake(mem, BODY)
        self.assertTrue(done)
        self.assertEqual(log, [('enter', CTRL + 0x50), ('transition', 0x5500, BODY),
                               ('leave', CTRL + 0x50)])
        self.assertEqual(mem.b(META + 0x53), 0x50)  # low nibble cleared
        self.assertEqual(mem.d(BODY + 0x28), 0)     # quiet timer zeroed
        # motion untouched
        self.assertEqual(mem.view(BODY + 0x1a0, 0x18).tobytes(), bytes(0x18))

    def test_metadata_bit0_and_null_group_gates(self):
        mem = make([(1, 0)])
        mem.set_b(META + 0x52, 1)
        self.assertEqual(self.run_wake(mem, BODY), (False, []))
        mem.set_b(META + 0x52, 0)
        mem.set_q(BODY + 0x10, 0)
        self.assertEqual(self.run_wake(mem, BODY), (False, []))
        self.assertEqual(mem.b(META + 0x53), 0x52)

    def test_stage_entry_uses_provider_plus_d0(self):
        mem = make([(1, 2)])
        mem.add(TREE - ACTION_TREE_OFFSET, bytearray(ACTION_TREE_OFFSET))
        log = []
        run_island_action_stage(mem, TREE - ACTION_TREE_OFFSET, 0.25,
                                update=lambda e, d: log.append('update'),
                                destroy=lambda e, f: log.append('destroy'),
                                enter=lambda s: log.append('enter'),
                                leave=lambda s: log.append('leave'),
                                transition=lambda c, b: log.append('transition'))
        self.assertEqual(log, ['update', 'enter', 'transition', 'leave', 'destroy'])


if __name__ == '__main__':
    unittest.main()
