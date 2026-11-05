"""Public tests for the composed island step (engine/pose_island_step.py).

These are independent implementation tests over synthetic fixtures. The native
byte-for-byte comparison lives in the private harness check_pose_island_step.py
(receipt native/snow_host/pose_island_step_validation.json).
"""
import math
import random
import struct
import unittest

from engine.pose_island_step import (RetainedRegions, diff_effects, replay_effects,
                                     native_crt_sort_prefix, capsule_resource_bounds,
                                     make_resource_bounds, IslandState, run_pose_island_step,
                                     default_island_stages, make_composed_batch_stage,
                                     make_command_preparation, BOUNDARIES, SUPPLIED_STAGES,
                                     bind_reconstructed_island_stages, RegionMemory)
from engine.pose_island_step_fixtures import (build_island_fixture, pack_settings,
                                              CAPSULE_RESOURCE_VTABLE, CALLBACK_OWNER_GLOBAL)
from engine.pose_contact_sort import sort_contact_records
from reference.central_impulse import f32


def u32(raw, off):
    return struct.unpack_from('<I', raw, off)[0]


def case(**overrides):
    c = dict(seed=7, dt=f32(1/30), settings={}, main_points=[2, 3], rider=True, rider_points=[1],
             free_group=True, fixed_group=True, quiet_group=True, quiet_contact=True,
             sleeping_group=False, changed='none', actions=0, callback=True, commands=(0, 0))
    c.update(overrides)
    return c


def float32_atan2(y, x):
    # Authored test substitute; the native harness replays observed atan2 outputs.
    return f32(math.atan2(y, x))


class Harness:
    """Run the model; bound=True binds the reconstructed C3/C4/C5/C6 modules, otherwise
    those stages are no-op replay services. C4 finish is always a no-op replay."""
    def __init__(self, fix, *, bound=False):
        self.fix = fix
        self.state = IslandState(fix['regions'], resources=fix['resources'], profiles=fix['profiles'],
                                 tokens=fix['tokens'])
        self.calls, self.labels, self.phases = [], [], []
        arenas = list(fix['tokens']['arenas'])
        self.released, self.alloc = [], []
        def allocate(size):
            self.alloc.append(size)
            return arenas.pop(0)
        batch = make_composed_batch_stage(self.state, atan2=float32_atan2, allocate=allocate,
            release_buffer=lambda t: None, release_payload=self.released.append,
            get_kind=lambda t: 2, observe=self.observe)
        def record(name):
            def service(*args):
                self.calls.append((name, args))
            return service
        def invoke(function, first, second, commands, count, reciprocal, mode, user):
            self.calls.append(('command_callback', (first, second, reciprocal, mode)))
            struct.pack_into('<I', count, 0, 7)
        self.stages = default_island_stages(self.state, batch_stage=batch,
            body_list_callback=record('body_list_callback'),
            prepare_constraint=make_command_preparation(self.state, invoke))
        for name in ('action_tree', 'stage_begin', 'stage_finish', 'attach_links'):
            self.stages[name] = replay_effects(self.state.regions, [], log=self.calls, name=name)
        self.stages['publish_link'] = record('publish_link')
        self.stages['notify_active'] = record('notify_active')
        if bound:
            effects = {e['entry']: e for e in fix['action_effects']}
            def update(entry, dt):
                e = effects[entry]
                body = self.state.maps['body'][e['body']]
                v = struct.unpack_from('<3f', body, 0x1a0)
                struct.pack_into('<3f', body, 0x1a0, *[f32(a + d) for a, d in zip(v, e['delta'])])
            b = bind_reconstructed_island_stages(self.state, action_update=update,
                action_destroy=record('destroy'), constraint_kind=lambda t: 2, log=self.calls,
                services=dict(publish_link=lambda *a: None, notify_active=lambda *a: None))
            for name in ('action_tree', 'stage_begin', 'stage_scalar', 'attach_links', 'publish_link',
                         'notify_active'):
                self.stages[name] = b[name]

    def observe(self, label, extra):
        self.labels.append(label)
        self.phases.append(u32(self.state.controller, 0x48))

    def run(self):
        run_pose_island_step(self.state, dt=self.fix['dt'], stages=self.stages, observe=self.observe)
        return self


class RegionTests(unittest.TestCase):
    def test_reads_and_writes_span_bytes_and_pointer_lists(self):
        r = RetainedRegions()
        a = bytearray(range(8))
        slots = [0x1111111111111111, 0x2222222222222222]
        r.add('a', 100, a)
        r.add('s', 108, slots)
        self.assertEqual(r.read(106, 4), bytes([6, 7, 0x11, 0x11]))
        r.write(107, b'\xaa\xbb\xcc')
        self.assertEqual(a[7], 0xaa)
        self.assertEqual(slots[0], 0x111111111111ccbb)
        r.write(116, struct.pack('<Q', 5))
        self.assertEqual(slots, [0x111111111111ccbb, 5])
        with self.assertRaises(KeyError):
            r.read(99, 2)
        with self.assertRaises(KeyError):
            r.write(124, b'\x00')

    def test_diff_then_replay_reproduces_effects_only(self):
        r = RetainedRegions()
        a = bytearray(16)
        r.add('a', 0, a)
        before = r.snapshot()
        after = dict(a=bytes([0, 1, 2, 0] + [0]*11 + [9]))
        effects = diff_effects(before, after, {'a': 0})
        self.assertEqual(effects, [(1, b'\x01\x02'), (15, b'\x09')])
        log = []
        replay_effects(r, effects, log=log, name='x')('arg')
        self.assertEqual(bytes(a), after['a'])
        self.assertEqual(log, [('x', ('arg',))])


class SortTests(unittest.TestCase):
    def test_generic_sort_matches_validated_record_permutation(self):
        rng = random.Random(3)
        for n in (0, 1, 2, 7, 8, 9, 16, 33, 64):
            keys = [rng.choice((1, 2, 3, 3, 5, 0xffffffff)) for _ in range(n)]
            records = [bytearray(48) for _ in range(n)]
            for i, (rec, k) in enumerate(zip(records, keys)):
                struct.pack_into('<I', rec, 44, k)
                struct.pack_into('<I', rec, 0, i)
            sort_contact_records(records, key_width=32)
            expected = [u32(rec, 0) for rec in records]
            slots = list(range(n))
            def cmp(a, b):
                d = (keys[a] - keys[b]) & 0xffffffff
                return d - 0x100000000 if d & 0x80000000 else d
            native_crt_sort_prefix(slots, n, cmp)
            self.assertEqual(slots, expected, n)

    def test_equal_keys_are_not_stable(self):
        slots = [10, 11, 12]
        native_crt_sort_prefix(slots, 3, lambda a, b: 0)
        self.assertEqual(slots, [11, 12, 10])


class BoundsTests(unittest.TestCase):
    def test_capsule_bounds_use_axis_row_and_radius(self):
        frame = [[1, 0, 0], [0, 0, 1], [0, -1, 0], [2, 3, 4]]
        self.assertEqual(capsule_resource_bounds(0.5, 0.25, frame),
                         [1.75, 2.75, 3.25, 2.25, 3.25, 4.75])

    def test_capsule_bounds_match_lane_implementation(self):
        from engine.pose_narrowphase_capsule_grid import capsule_local_bounds
        bits = lambda v: struct.unpack('<I', struct.pack('<f', v))[0]
        rng = random.Random(11)
        for _ in range(200):
            frame = [[f32(rng.uniform(-2, 2)) for _ in range(3)] for _ in range(4)]
            h, r = f32(rng.uniform(0, 1)), f32(rng.uniform(0, 0.3))
            lanes = capsule_local_bounds(bits(h), bits(r), [[bits(v) for v in row] + [0] for row in frame], 'sse')
            self.assertEqual([bits(v) for v in capsule_resource_bounds(h, r, frame)], lanes)

    def test_unknown_resource_class_is_rejected(self):
        raw = bytearray(0xc0)
        struct.pack_into('<Q', raw, 0, 0x1234)
        with self.assertRaises(ValueError):
            make_resource_bounds({5: raw})(5, [[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 0, 0]])
        struct.pack_into('<Q', raw, 0, CAPSULE_RESOURCE_VTABLE)
        struct.pack_into('<2f', raw, 0x40, 1.0, 0.5)
        self.assertEqual(make_resource_bounds({5: raw})(5, [[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 0, 0]]),
                         [-0.5, -1.5, -0.5, 0.5, 1.5, 0.5])


class SettingsTests(unittest.TestCase):
    def test_packed_world_settings_offsets(self):
        raw = pack_settings({'iterations': 3, 'secondary': 5, 'mode': 2, 'cache': 0, 'duration': 0.25})
        self.assertEqual(struct.unpack_from('<3f', raw, 8), (0.0, 0.0, f32(-9.81)))
        self.assertEqual(struct.unpack_from('<IHH', raw, 0x24), (2, 3, 5))
        self.assertEqual(raw[0x21], 0)
        self.assertEqual(struct.unpack_from('<f', raw, 0x34)[0], 0.25)


class BoundStageTests(unittest.TestCase):
    def test_region_memory_reads_writes_and_views(self):
        r = RetainedRegions()
        a = bytearray(16)
        r.add('a', 0x100, a)
        r.add('s', 0x110, [7, 8])
        m = RegionMemory(r)
        m.set_d(0x104, 0xdeadbeef)
        self.assertEqual(m.d(0x104), 0xdeadbeef)
        self.assertEqual(m.q(0x118), 8)
        m.set_q(0x110, 9)
        self.assertEqual(r.items[1][2][0], 9)
        m.view(0x100, 4)[:] = b'\x01\x02\x03\x04'
        self.assertEqual(bytes(a[:4]), b'\x01\x02\x03\x04')
        with self.assertRaises(KeyError):
            m.view(0x110, 8)

    def test_wake_attach_publish_and_notify(self):
        fix = build_island_fixture(case(sleeping_group=True, changed='wake', actions=3, action_remove=True,
                                        quiet_group=False))
        h = Harness(fix, bound=True)
        bp = h.state.named['interface']
        vec = h.state.named['bp_vector']
        used = u32(vec, 8)
        h.run()
        isl = h.state.island
        sleeper = h.state.addresses['group:sleeper']
        self.assertEqual(h.state.maps['group'][sleeper][0xa0], 0)
        actives = h.state.arrays[h.state.addresses['array:active']][:u32(isl, 0x420)]
        self.assertIn(sleeper, actives)
        published = [c[1] for c in h.calls if c[0] == 'publish_link']
        self.assertTrue(published)
        self.assertEqual(u32(vec, 8), used + len(published))
        cb = [c[1] for c in h.calls if c[0] == 'body_list_callback'][0]
        self.assertEqual(cb[5], 1)                       # sleeper body in the wake list
        self.assertEqual(h.state.arrays[cb[4]][0], h.state.addresses['body:sleeper'])
        self.assertTrue(bp[0x49] & 1)                    # active groups remain: +0xa8 marked
        self.assertEqual(sum(1 for c in h.calls if c[0] == 'destroy'), 1)
        changed = h.state.addresses['link:changed']
        sleeper_links = h.state.arrays[h.state.addresses['array:sleeper_links']]
        self.assertIn(changed, sleeper_links[:u32(h.state.maps['group'][sleeper], 0x48)])

    def test_bound_and_noop_stages_agree_without_island_events(self):
        # With no actions, no changed links and no pending links, C3/C5 are no-ops
        # apart from attach clearing the pending count.
        fix = build_island_fixture(case(changed='none', actions=0))
        a = Harness(fix, bound=True).run().state
        b = Harness(fix, bound=False).run().state
        self.assertEqual(u32(a.island, 0x498), 0)
        diff = [n for n, raw in a.regions.snapshot().items() if raw != b.regions.snapshot()[n]]
        self.assertTrue(set(diff) <= {'island', 'interface'}, diff)


class OrchestrationTests(unittest.TestCase):
    def test_missing_stage_is_an_error(self):
        h = Harness(build_island_fixture(case()))
        del h.stages['attach_links']
        with self.assertRaises(ValueError):
            h.run()

    def test_boundary_order_phase_and_services(self):
        h = Harness(build_island_fixture(case(commands=(1, 1)))).run()
        top = [l for l in h.labels if l != 'poststep']
        self.assertEqual(top, list(BOUNDARIES))
        posts = [i for i, l in enumerate(h.labels) if l == 'poststep']
        self.assertTrue(posts and h.labels.index('C6') < posts[0] < h.labels.index('C7-D10'))
        self.assertEqual(h.phases[:h.labels.index('C7-D10') + 1], [3] * (h.labels.index('C7-D10') + 1))
        self.assertEqual(h.phases[-3:], [0, 0, 0])
        names = [c[0] for c in h.calls]
        self.assertEqual(names.index('command_callback'), 0)
        self.assertLess(names.index('action_tree'), names.index('stage_begin'))
        self.assertLess(names.index('stage_finish'), names.index('attach_links'))
        cmd = [c[1] for c in h.calls if c[0] == 'command_callback']
        self.assertEqual(len(cmd), 2)
        self.assertEqual(cmd[0][2], f32(1 / h.fix['dt']))
        self.assertEqual(cmd[0][3], 1)
        # count above six is reset by the recovered wrapper
        for token, raw in h.state.maps['command'].items():
            self.assertEqual(u32(raw, 0x74), 0)
        self.assertEqual(struct.unpack_from('<f', h.state.stage, 0x10)[0], h.fix['dt'])
        isl = h.state.island
        self.assertEqual((u32(isl, 0x478), u32(isl, 0x488)), (0, 0))

    def test_gravity_free_motion_and_solver_groups(self):
        fix = build_island_fixture(case(fixed_group=False, quiet_group=False))
        free = [r for r in fix['regions'] if r.name == 'body:free'][0]
        before = struct.unpack_from('<3f', free.data, 0x1a0)
        flags = free.data[0xaa]
        h = Harness(fix).run()
        after = struct.unpack_from('<3f', h.state.named['body:free'], 0x1a0)
        g = f32(f32(1/30) * f32(-9.81))
        expected_z = before[2] if flags & 8 else f32(before[2] + g)
        self.assertEqual(after[2], expected_z)
        self.assertEqual(after[:2], before[:2])
        main = h.state.named['body:main']
        self.assertNotEqual(bytes(main[0x40:0x80]), bytes(fix['regions'][[r.name for r in fix['regions']].index('body:main')].data[0x40:0x80]))
        self.assertEqual(len(h.alloc), 1)
        self.assertEqual(h.labels.count('poststep'), 2)

    def test_everything_settles_skips_notify_and_reports_sleep_list(self):
        fix = build_island_fixture(case(settings=dict(linear=50.0, angular=50.0, duration=0.001)))
        h = Harness(fix).run()
        names = [c[0] for c in h.calls]
        self.assertNotIn('notify_active', names)
        isl = h.state.island
        self.assertEqual(u32(isl, 0x420), 0)
        callback = [c[1] for c in h.calls if c[0] == 'body_list_callback'][0]
        _, controller, sleep, sleep_count, wake, wake_count = callback
        self.assertEqual(controller, fix['tokens']['controller'])
        self.assertEqual(sleep_count, 5)          # main, rider, free, fixed, quiet
        self.assertEqual(wake_count, 0)
        self.assertEqual(sorted(h.state.arrays[sleep][:5]),
                         sorted(a for n, a in h.state.addresses.items()
                                if n in ('body:main', 'body:rider', 'body:free', 'body:fixed', 'body:quiet')))
        self.assertEqual(u32(isl, 0x488), 0)
        self.assertTrue(h.released)               # inactive transition retired contact payloads

    def test_active_groups_notify_once_and_null_callback_owner_slot(self):
        fix = build_island_fixture(case(callback=False, quiet_group=False))
        h = Harness(fix).run()
        names = [c[0] for c in h.calls]
        self.assertEqual(names.count('notify_active'), 1)
        self.assertEqual([c[1] for c in h.calls if c[0] == 'notify_active'][0], (fix['tokens']['interface'], 0))
        self.assertNotIn('body_list_callback', names)

    def test_deterministic_repeat(self):
        a = Harness(build_island_fixture(case(second_rider=True))).run().state.regions.snapshot()
        b = Harness(build_island_fixture(case(second_rider=True))).run().state.regions.snapshot()
        self.assertEqual(a, b)

    def test_stage_effects_ordering_matters(self):
        # A supplied C3 effect that nudges the main body's velocity must be seen by the solve.
        fix = build_island_fixture(case(rider=False, main_points=[], free_group=False, fixed_group=False,
                                        quiet_group=False))
        base = Harness(fix).run().state.named['body:main']
        h = Harness(fix)
        main = fix['tokens']['main']
        h.stages['action_tree'] = replay_effects(h.state.regions,
            [(main + 0x1a0, struct.pack('<f', f32(struct.unpack_from('<f', h.state.named['body:main'], 0x1a0)[0] + 1.0)))])
        moved = h.run().state.named['body:main']
        self.assertNotEqual(bytes(base[0x70:0x7c]), bytes(moved[0x70:0x7c]))

    def test_supplied_stage_list_is_explicit(self):
        self.assertEqual(set(SUPPLIED_STAGES), {'action_tree', 'stage_begin', 'stage_finish', 'attach_links',
                                                'publish_link', 'notify_active', 'body_list_callback'})


if __name__ == '__main__':
    unittest.main()
