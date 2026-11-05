import struct
import unittest
from engine.pose_body_state_setters import (set_pose_body_angular_velocity,
    set_pose_body_linear_velocity, set_pose_body_pose)
from engine.pose_body_controller_transition import transition_controller_pose_body
from engine.pose_body_group_transition import transition_pose_body_group

META, HOLDER, CTRL, CTX = 3, 7, 9, 4


def fixture(kind=0, controller=CTRL):
    body = bytearray(0x200)
    meta = bytearray(0x60)
    holder = bytearray(0x40)
    struct.pack_into('<Q', body, 0x30, META)
    struct.pack_into('<Q', body, 0x10, 5)
    struct.pack_into('<Q', meta, 0x20, HOLDER)
    struct.pack_into('<Q', holder, 0x20, controller)
    meta[0x53] = kind
    return body, {META: meta}, {HOLDER: holder}


class SetterGateTests(unittest.TestCase):
    def run_setter(self, fn, off, kind, force, controller=CTRL):
        body, md, hd = fixture(kind, controller)
        calls = []
        vec = bytes(range(1, 13))
        fn(body, vec, force, metadata=md, holders=hd,
           notify=lambda *a: calls.append(a), body_token=2)
        return body, calls, vec

    def test_linear_and_angular_store_and_notify_gates(self):
        for fn, off in ((set_pose_body_linear_velocity, 0x1a0),
                        (set_pose_body_angular_velocity, 0x1ac)):
            for kind in (0, 1, 2, 0x32, 0xf2):
                for force in (0, 1, 0x100, 0x80):
                    for controller in (0, CTRL):
                        body, calls, vec = self.run_setter(fn, off, kind, force, controller)
                        stored = kind & 15 != 2 or force & 255
                        self.assertEqual(bytes(body[off:off + 12]),
                                         vec if stored else bytes(12))
                        want = [(controller, 2)] if controller and force & 255 else []
                        self.assertEqual(calls, want)

    def test_kind2_without_force_skips_store_and_notify(self):
        body, calls, _ = self.run_setter(set_pose_body_linear_velocity, 0x1a0, 2, 0)
        self.assertEqual(bytes(body[0x1a0:0x1ac]), bytes(12))
        self.assertEqual(calls, [])

    def test_pose_notifies_without_force_and_needs_only_controller(self):
        for controller in (0, CTRL):
            body, md, hd = fixture(2, controller)
            ev = []
            set_pose_body_pose(body, bytes(range(48)), metadata=md, holders=hd,
                               store_pose=lambda *a: ev.append(('pose', *a)),
                               notify=lambda *a: ev.append(('notify', *a)), body_token=2)
            rows = tuple(bytes(range(i, i + 12)) for i in range(0, 48, 12))
            self.assertEqual(ev[0], ('pose', 2, rows))
            self.assertEqual(ev[1:], [('notify', CTRL, 2)] if controller else [])


class CompositionTests(unittest.TestCase):
    """velocity set -> transition wrapper -> group transition (existing modules)."""

    def compose(self, force, flags52, kind53, group, selected, special_equal, virtual8,
                m50=0, controller=CTRL, preds=None):
        body, md, hd = fixture(0, controller)
        m = md[META]
        m[0x52] = flags52
        m[0x53] = kind53
        struct.pack_into('<H', m, 0x50, m50)
        struct.pack_into('<Q', body, 0x10, group)
        ctx = bytearray(0x420)
        struct.pack_into('<QQ', ctx, 0x408, 111, 222)
        if special_equal:
            struct.pack_into('<Q', body, 0x10, 222)
        events = []
        seq = list(preds) if preds else [selected, selected]
        ctrl = bytearray(0x80)
        struct.pack_into('<Q', ctrl, 0x30, CTX)

        def transition(ctx_token, body_token):
            def remove(c, b):
                events.append(('remove', c, b))   # 18e23c0: pool 0x143336bb8 reachable
                struct.pack_into('<Q', body, 0x10, 0)

            def obtain(c):
                events.append(('obtain', c))      # 18e19c0: pool 0x143336aa0
                return 333
            transition_pose_body_group(ctx, body, context_token=ctx_token,
                body_token=body_token, metadata=md,
                predicate=lambda *a: seq.pop(0), remove_body=remove,
                body_virtual8=lambda *a: virtual8, obtain_group=obtain,
                reset_body=lambda b: events.append(('reset_virtual', b)),
                append_body=lambda t, b: (events.append(('append', t, b)),
                                          struct.pack_into('<Q', body, 0x10, t)),
                finalize=lambda c, g: events.append(('finalize', c, g)))

        def notify(controller_token, body_token):
            events.append(('wrapper', controller_token))
            transition_controller_pose_body(ctrl, body, controller_token=controller_token,
                body_token=body_token, metadata=md,
                enter=lambda s: events.append(('enter', s)),
                leave=lambda s: events.append(('leave', s)),
                transition=transition,
                reset_body=lambda b: events.append(('reset', b)))
        set_pose_body_linear_velocity(body, bytes(12), force, metadata=md, holders=hd,
                                      notify=notify, body_token=2)
        return events

    def test_force_zero_never_reaches_wrapper(self):
        self.assertEqual(self.compose(0, 8, 0, 5, 1, False, 1), [])

    def test_wrapper_gate_flags52_bit0_stops_before_lock(self):
        self.assertEqual(self.compose(1, 9, 0, 5, 1, False, 1), [('wrapper', CTRL)])

    def test_unflagged_group_only_finalizes(self):
        ev = self.compose(1, 0, 0, 5, 1, False, 1)
        self.assertEqual([e[0] for e in ev], ['wrapper', 'enter', 'finalize', 'reset', 'leave'])

    def test_selection_change_reaches_remove_and_obtain(self):
        # bit15 set, second predicate false: remove (bb8 via 1958720 links) then obtain (aa0)
        ev = self.compose(1, 8, 0, 5, 1, False, 1, m50=0x8000, preds=[1, 0])
        self.assertEqual([e[0] for e in ev], ['wrapper', 'enter', 'remove', 'obtain',
                                             'append', 'finalize', 'reset', 'leave'])

    def test_bit15_clear_targets_group408_without_obtain(self):
        ev = self.compose(1, 8, 0, 5, 1, False, 1, m50=0)
        self.assertEqual([e[0] for e in ev], ['wrapper', 'enter', 'remove', 'append',
                                             'finalize', 'reset', 'leave'])
        self.assertEqual(ev[3], ('append', 111, 2))

    def test_special_group_target_skips_obtain(self):
        ev = self.compose(1, 8, 0, 5, 1, False, 1, m50=0x8000, preds=[1, 1])
        self.assertEqual([e[0] for e in ev], ['wrapper', 'enter', 'remove', 'append',
                                             'finalize', 'reset', 'leave'])
        self.assertEqual(ev[3], ('append', 222, 2))

    def test_no_selection_change_reaches_no_pool_service(self):
        ev = self.compose(1, 8, 0, 5, 0, False, 1, preds=[0])
        self.assertNotIn('remove', [e[0] for e in ev])
        self.assertNotIn('obtain', [e[0] for e in ev])


if __name__ == '__main__':
    unittest.main()
