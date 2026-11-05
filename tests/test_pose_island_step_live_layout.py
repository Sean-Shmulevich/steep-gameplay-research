"""Tests for the live-layout support of the composed island step.

LINK_SOLVER.md "Composed island step on live substeps": inline small-buffer arrays,
damping and quiet-override pass-through, sphere resource bounds 0x18c75a0 and the
static body class 0x29c98c8. Fixtures are the authored synthetic island fixtures,
relocated in-test into the live inline layouts. The native comparisons live in the
private harnesses (check_pose_sphere_bounds.py, sr_replay_engine.py).
"""
import random
import struct
import unittest

from engine.pose_island_step import (RetainedRegions, InlinePointerArray, FloatRecords, IslandState,
                                     INLINE_SMALL_BUFFERS, LIVE_RECORD_SPACING, RegionMemory,
                                     sphere_resource_bounds, capsule_resource_bounds,
                                     make_resource_bounds, make_composed_batch_stage,
                                     default_island_stages, replay_effects, run_pose_island_step)
from engine.pose_island_step_fixtures import (build_island_fixture, Region, SPHERE_RESOURCE_VTABLE,
                                              STATIC_BODY_VTABLE, BODY_VTABLE)
from reference.central_impulse import f32

IDENTITY = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def bits(v):
    return struct.unpack('<I', struct.pack('<f', v))[0]


def case(**overrides):
    c = dict(seed=7, dt=f32(1 / 30), settings={}, main_points=[2, 3], rider=True, rider_points=[1],
             free_group=True, fixed_group=True, quiet_group=True, quiet_contact=True,
             sleeping_group=False, changed='none', actions=0, callback=True, commands=(0, 0))
    c.update(overrides)
    return c


def atan2(y, x):
    import math
    return f32(math.atan2(y, x))


def by_name(fix, name):
    return next(r for r in fix['regions'] if r.name == name)


def relocate_inline(fix):
    """Move storage into the live inline layouts (authored test transform).

    Groups with <= 4 bodies / <= 8 links get them at group+0x20 / +0x50; links with
    <= 1 entry at link+0x68; single-shape bodies at body+0xc8. The separate regions are
    dropped. Returns the set of (category, token) relocated.
    """
    regions = {r.address: r for r in fix['regions']}
    moved = set()
    for category, field, (count_at, fmt), offset, capacity, size, target in INLINE_SMALL_BUFFERS:
        for r in list(regions.values()):
            if r.category != category:
                continue
            pointer = struct.unpack_from('<Q', r.data, field)[0]
            count = struct.unpack_from(fmt, r.data, count_at)[0]
            source = regions.get(pointer)
            if source is None or count > capacity or (category == 'body' and count != 1):
                continue
            raw = source.raw()
            r.data[offset:offset + capacity * size] = raw[:capacity * size].ljust(capacity * size, b'\0')
            struct.pack_into('<Q', r.data, field, r.address + offset)
            if fmt == '<I':
                struct.pack_into('<I', r.data, count_at + 4, capacity)
            del regions[pointer]
            moved.add((category, r.address, field))
    fix['regions'] = sorted(regions.values(), key=lambda r: r.address)
    return moved


def free_address(fix, size=0x100):
    top = max(r.address + r.size for r in fix['regions'])
    return (top + 0xff) & ~0xff


class Run:
    """Composed step with no-op replays for C3/C4/C5 (as test_pose_island_step.Harness)."""
    def __init__(self, fix, **batch_kwargs):
        self.state = IslandState(fix['regions'], resources=fix['resources'], profiles=fix['profiles'],
                                 tokens=fix['tokens'])
        self.fix = fix
        arenas = list(fix['tokens']['arenas'])
        batch = make_composed_batch_stage(self.state, atan2=atan2, allocate=lambda size: arenas.pop(0),
            release_buffer=lambda t: None, release_payload=lambda t: None, get_kind=lambda t: 2,
            **batch_kwargs)
        self.stages = default_island_stages(self.state, batch_stage=batch,
            body_list_callback=lambda *a: None, prepare_constraint=lambda *a: None)
        for name in ('action_tree', 'stage_begin', 'stage_finish', 'attach_links'):
            self.stages[name] = replay_effects(self.state.regions, [])
        self.stages['publish_link'] = lambda *a: None
        self.stages['notify_active'] = lambda *a: None

    def run(self):
        run_pose_island_step(self.state, dt=self.fix['dt'], stages=self.stages)
        return self.state.regions.snapshot()


class InlineArrayTests(unittest.TestCase):
    def test_inline_pointer_array_reads_and_writes_containing_record(self):
        record = bytearray(0x40)
        struct.pack_into('<2Q', record, 0x20, 11, 22)
        view = InlinePointerArray(record, 0x20, 4)
        self.assertEqual(len(view), 4)
        self.assertEqual(view[:2], [11, 22])
        self.assertEqual(view[-1], 0)
        view[1] = 0x1234
        view[2:4] = [5, 6]
        self.assertEqual(struct.unpack_from('<4Q', record, 0x20), (11, 0x1234, 5, 6))
        self.assertEqual(list(view), [11, 0x1234, 5, 6])
        with self.assertRaises(IndexError):
            view[4]
        with self.assertRaises(ValueError):
            view[0:2] = [1]
        with self.assertRaises(ValueError):
            InlinePointerArray(record, 0x30, 4)

    def test_regions_reject_overlap_and_find_container(self):
        r = RetainedRegions()
        r.add('group', 0x1000, bytearray(0xa8))
        r.add('slots', 0x2000, [0, 0])
        with self.assertRaises(ValueError):
            r.add('inner', 0x1020, bytearray(0x20))
        with self.assertRaises(ValueError):
            r.add('tail', 0x10a0, bytearray(0x10))
        r.add('adjacent', 0x10a8, bytearray(8))
        self.assertEqual(r.container(0x1020, 0x20)[:2], ('group', 0x1000))
        self.assertIsNone(r.container(0x10a0, 0x10))      # spans two regions
        self.assertIsNone(r.container(0x2000, 8))         # pointer-list region has no byte view

    def test_state_binds_live_inline_layouts(self):
        fix = build_island_fixture(case())
        moved = relocate_inline(fix)
        kinds = {(c, f) for c, _, f in moved}
        self.assertEqual(kinds, {('group', 0x10), ('group', 0x40), ('link', 0x58), ('body', 0xb8)})
        state = Run(fix).state
        for category, token, field in moved:
            pointer = token + {0x10: 0x20, 0x40: 0x50, 0x58: 0x68, 0xb8: 0xc8}[field]
            if category == 'group':
                view = state.arrays[pointer]
                self.assertIsInstance(view, InlinePointerArray)
                self.assertEqual(len(view), 4 if field == 0x10 else 8)
                # A write through the view is a write into the group record (and memory view).
                old = view[0]
                view[0] = 0xabcdef
                self.assertEqual(RegionMemory(state.regions).q(pointer), 0xabcdef)
                view[0] = old
            else:
                view = state.entry_arrays[pointer]
                self.assertIsInstance(view, memoryview)
                self.assertEqual(len(view), 16 if category == 'link' else 72)
                self.assertEqual(bytes(view), bytes(state.maps[category][token][pointer - token:
                                                                                  pointer - token + len(view)]))
        self.assertEqual(len(state.inline), len(moved))

    def test_inline_binding_is_optional_and_checks_capacity(self):
        fix = build_island_fixture(case())
        relocate_inline(fix)
        state = IslandState(fix['regions'], resources=fix['resources'], profiles=fix['profiles'],
                            tokens=fix['tokens'], inline_buffers=False)
        self.assertEqual(state.inline, [])
        group = next(r for r in fix['regions'] if r.category == 'group'
                     and struct.unpack_from('<Q', r.data, 0x10)[0] == r.address + 0x20)
        struct.pack_into('<I', group.data, 0x18, 5)            # 5 bodies cannot be inline
        with self.assertRaises(ValueError):
            IslandState(fix['regions'], resources=fix['resources'], profiles=fix['profiles'],
                        tokens=fix['tokens'])

    def test_inline_layout_step_equals_separate_layout_step(self):
        for seed in (7, 8, 9, 21):
            c = case(seed=seed)
            plain = Run(build_island_fixture(c)).run()
            fix = build_island_fixture(c)
            moved = relocate_inline(fix)
            inline = Run(fix).run()
            # Untouched records match byte for byte.
            for name, data in inline.items():
                if not name.startswith(('group:', 'link:', 'body:')):
                    self.assertEqual(data, plain[name], (seed, name))
            # Containers match outside the pointer/capacity fields and inline storage.
            for name, data in inline.items():
                if not name.startswith(('group:', 'link:', 'body:')):
                    continue
                mask = set()
                for category, field, (count_at, fmt), offset, capacity, size, _ in INLINE_SMALL_BUFFERS:
                    if name.startswith(category + ':'):
                        mask |= set(range(field, field + 8)) | set(range(count_at + 4, count_at + 8)) if fmt == '<I' \
                            else set(range(field, field + 8))
                        mask |= set(range(offset, offset + capacity * size))
                diff = [i for i in range(len(data)) if i not in mask and data[i] != plain[name][i]]
                self.assertEqual(diff, [], (seed, name))
            self.assertTrue(moved)

    def test_live_record_spacing_holds_inline_storage(self):
        for category, field, _, offset, capacity, size, _ in INLINE_SMALL_BUFFERS:
            if category in LIVE_RECORD_SPACING:
                self.assertLessEqual(offset + capacity * size, LIVE_RECORD_SPACING[category])
        self.assertEqual(LIVE_RECORD_SPACING, dict(link=0x88, resource=0x48, body=0x1d0))


class DampingAndQuietTests(unittest.TestCase):
    def with_records(self, *, damping=None, override=None):
        fix = build_island_fixture(case())
        main = fix['tokens']['main'] if 'main' in fix['tokens'] else next(
            r.address for r in fix['regions'] if r.name == 'body:main')
        body = next(r for r in fix['regions'] if r.address == main)
        at = free_address(fix)
        if damping is not None:
            raw = bytearray(struct.pack('<4f', *damping))
            fix['regions'].append(Region('damping:main', at, 'bytes', raw, 'damping'))
            struct.pack_into('<Q', body.data, 0x1b8, at)
            at += 0x10
        if override is not None:
            raw = bytearray(struct.pack('<3f', *override))
            fix['regions'].append(Region('quiet_override:main', at, 'bytes', raw, 'quiet_override'))
            struct.pack_into('<Q', body.data, 0x1c0, at)
        return fix, main

    def test_float_records_decode_retained_bytes(self):
        records = {0x10: bytearray(struct.pack('<4f', 0.5, 0.25, 0.125, 1.0))}
        view = FloatRecords(records, 4)
        self.assertEqual(view[0x10], [0.5, 0.25, 0.125, 1.0])
        records[0x10][0:4] = struct.pack('<f', 2.0)
        self.assertEqual(view[0x10][0], 2.0)
        self.assertEqual(list(view), [0x10])

    def test_damping_records_and_response_are_passed_through(self):
        record = (0.8, 0.8, 0.8, 0.2)
        fix, main = self.with_records(damping=record)
        calls = []
        def response(base, s):
            calls.append((list(base), s))
            return [0.5, 0.5, 0.5, 0.5]
        run = Run(fix, damping_response=response)
        self.assertEqual(run.state.damping_records[struct.unpack_from('<Q', run.state.maps['body'][main], 0x1b8)[0]],
                         [f32(v) for v in record])
        damped = run.run()
        self.assertTrue(calls)
        for base, s in calls:
            self.assertEqual([bits(v) for v in base], [bits(f32(1.0 - f32(v))) for v in record])
            self.assertNotEqual(s, 0)
        fix2, _ = self.with_records(damping=record)
        undamped = Run(fix2, damping_response=lambda base, s: [1.0] * 4).run()
        self.assertNotEqual(damped['body:main'][0x1a0:0x1b8], undamped['body:main'][0x1a0:0x1b8])

    def test_reached_damping_without_response_raises(self):
        fix, _ = self.with_records(damping=(0.8, 0.8, 0.8, 0.2))
        with self.assertRaises(ValueError):
            Run(fix).run()

    def test_explicit_damping_mapping_overrides_state_regions(self):
        fix, main = self.with_records(damping=(0.8, 0.8, 0.8, 0.2))
        token = struct.unpack_from('<Q', by_name(fix, 'body:main').data, 0x1b8)[0]
        seen = []
        def response(base, s):
            seen.append(list(base))
            return [1.0] * 4
        Run(fix, damping_records={token: [0.0, 0.0, 0.0, 0.0]}, damping_response=response).run()
        self.assertTrue(seen)
        self.assertTrue(all(b == [1.0] * 4 for b in seen))

    def test_quiet_overrides_are_passed_through(self):
        fix, main = self.with_records(override=(0.1, 0.0159155, 1.0))
        token = struct.unpack_from('<Q', by_name(fix, 'body:main').data, 0x1c0)[0]
        accessed = []
        class Recording(dict):
            def __getitem__(self, key):
                accessed.append(key)
                return dict.__getitem__(self, key)
        state_default = Run(fix).run()
        fix2, _ = self.with_records(override=(0.1, 0.0159155, 1.0))
        explicit = Run(fix2, quiet_overrides=Recording({token: [f32(0.1), f32(0.0159155), 1.0]})).run()
        self.assertIn(token, accessed)
        self.assertEqual(state_default, explicit)

    def test_reached_override_without_record_raises(self):
        fix, _ = self.with_records(override=(0.1, 0.0159155, 1.0))
        fix['regions'] = [r for r in fix['regions'] if r.category != 'quiet_override']
        with self.assertRaises(ValueError):
            Run(fix).run()


class SphereBoundsTests(unittest.TestCase):
    def test_operand_order_and_signed_zero(self):
        frame = IDENTITY + [[2.0, -3.0, 0.5]]
        self.assertEqual(sphere_resource_bounds(0.25, frame), [1.75, -3.25, 0.25, 2.25, -2.75, 0.75])
        low_high = sphere_resource_bounds(0.0, IDENTITY + [[0.0, -0.0, 1.0]])
        # low = t - r: (+0) - (+0) = +0, (-0) - (+0) = -0; high = r + t: (+0) + (-0) = +0.
        self.assertEqual([bits(v) for v in low_high[:2]], [0, 0x80000000])
        self.assertEqual(bits(low_high[4]), 0)
        self.assertEqual(sphere_resource_bounds(-0.0, IDENTITY + [[-0.0, 0, 0]])[3], -0.0)
        self.assertEqual(bits(sphere_resource_bounds(-0.0, IDENTITY + [[-0.0, 0, 0]])[3]), 0x80000000)

    def test_ignores_rotation_and_equals_zero_height_capsule(self):
        rng = random.Random(0x18c75a0)
        for _ in range(500):
            frame = [[f32(rng.uniform(-3, 3)) for _ in range(3)] for _ in range(4)]
            r = f32(rng.uniform(0, 1))
            out = sphere_resource_bounds(r, frame)
            self.assertEqual(out, sphere_resource_bounds(r, IDENTITY + [frame[3]]))
            self.assertEqual([bits(v) for v in out],
                             [bits(v) for v in capsule_resource_bounds(0.0, r, frame)])

    def test_dispatch_by_sphere_vtable(self):
        raw = bytearray(0x48)
        struct.pack_into('<Q', raw, 0, SPHERE_RESOURCE_VTABLE)
        struct.pack_into('<2f', raw, 0x40, 0.5, 99.0)         # +0x44 is not read
        frame = IDENTITY + [[1.0, 2.0, 3.0]]
        self.assertEqual(make_resource_bounds({7: raw})(7, frame), [0.5, 1.5, 2.5, 1.5, 2.5, 3.5])

    def test_native_receipt(self):
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / 'native/snow_host/pose_sphere_bounds_validation.json'
        receipt = json.loads(path.read_text())
        self.assertEqual(receipt['entry_rva'], '0x18c75a0')
        self.assertGreaterEqual(receipt['cases'], 256)
        self.assertEqual(receipt['passed'], receipt['cases'])

    def test_sphere_and_static_vtables(self):
        self.assertEqual(SPHERE_RESOURCE_VTABLE, 0x1429C9BE8)
        self.assertEqual(STATIC_BODY_VTABLE, 0x1429C98C8)


class BodyClassTests(unittest.TestCase):
    def test_static_body_class_in_integrated_group_is_rejected(self):
        fix = build_island_fixture(case())
        body = by_name(fix, 'body:main')
        self.assertEqual(struct.unpack_from('<Q', body.data, 0)[0], BODY_VTABLE)
        struct.pack_into('<Q', body.data, 0, STATIC_BODY_VTABLE)
        with self.assertRaises(ValueError) as caught:
            Run(fix).run()
        self.assertIn('class', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
