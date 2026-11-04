import struct
import unittest
from engine.pose_body_connectivity_rebuild import rebuild_pose_body_connectivity
from engine.pose_group_link_remove import DETACHED, remove_pose_group_link
from engine.pose_group_process import process_pose_group
from engine.pose_group_process_bytes import (
    QwordArray, make_pose_group_process, process_pose_group_bytes)

CTX, GROUP, SLOTS = 1, 30, 700


def build(flags, count, declared=None):
    """Synthetic byte state: group 30 with body tokens 100.. and per-body metadata."""
    ctx = bytearray(0x470)
    struct.pack_into('<Q', ctx, 0x410, 55)
    group = bytearray(0x100)
    struct.pack_into('<QI', group, 0x10, SLOTS, count if declared is None else declared)
    slots = bytearray(8 * 8)
    bodies, metadata = {}, {}
    for i in range(count):
        struct.pack_into('<Q', slots, i * 8, 100 + i)
        body = bytearray(0x80)
        struct.pack_into('<Q', body, 0x30, 900 + i)
        meta = bytearray(0x80)
        meta[0x52] = flags[i]
        bodies[100 + i], metadata[900 + i] = body, meta
    return ctx, group, slots, bodies, metadata


class Recorder:
    def __init__(self, ctx, group, eligible_result=1, finalize_count=None, seeds=None,
                 components=0):
        self.events, self.ctx, self.group = [], ctx, group
        self.eligible_result, self.finalize_count = eligible_result, finalize_count
        self.seeds, self.components = seeds, components
        self.storage = None

    def services(self):
        ev = self.events

        def finalize(c, g):
            ev.append('finalize')
            if self.finalize_count is not None:
                struct.pack_into('<I', self.group, 0x18, self.finalize_count)

        def eligible(c, b):
            ev.append(('eligible', b))
            struct.pack_into('<Q', self.ctx, 0x410, 56)
            return self.eligible_result

        def remove_body(g, b):
            ev.append(('remove_body', g, b))
            struct.pack_into('<Q', self.ctx, 0x410, 57)

        def append_body(dest, b):
            ev.append(('append', dest, b))
            return False

        def allocate(n):
            ev.append(('allocate', n))
            self.storage = bytearray(b'\xee' * n)
            return self.storage

        def prepare(c, g, d):
            ev.append(('prepare', d['count']))
            d['slots'][:] = self.seeds or [0] * d['count']
            return self.components

        def migrate(g, d):
            ev.append(('migrate', d['count'], list(d['slots'])))
            struct.pack_into('<I', self.group, 0x18, 0)

        return dict(finalize=finalize, eligible=eligible, remove_body=remove_body,
                    append_body=append_body, allocate=allocate, prepare=prepare,
                    acquire_group=lambda c: ev.append('acquire') or 77, migrate=migrate,
                    release=lambda s: ev.append('release'),
                    remove_group=lambda c, g: ev.append(('remove_group', c, g)),
                    destroy=lambda g, a: ev.append(('destroy', g, a)))


def run(flags, count=None, **kw):
    count = len(flags) if count is None else count
    ctx, group, slots, bodies, metadata = build(flags, count)
    rec = Recorder(ctx, group, **kw)
    result = process_pose_group_bytes(
        CTX, GROUP, contexts={CTX: ctx}, groups={GROUP: group}, bodies=bodies,
        metadata=metadata, slot_arrays={SLOTS: slots}, **rec.services())
    return result, rec, ctx, group


class ByteAdapterTests(unittest.TestCase):
    def test_qword_array_round_trip(self):
        buf = bytearray(24)
        a = QwordArray(buf)
        a[:] = [1, 2, 0xFFFFFFFF_FFFFFFFF]
        self.assertEqual(list(a), [1, 2, 0xFFFFFFFF_FFFFFFFF])
        self.assertEqual(struct.unpack('<QQQ', buf), (1, 2, 0xFFFFFFFF_FFFFFFFF))
        with self.assertRaises(IndexError):
            a[3]
        with self.assertRaises(ValueError):
            a[:] = [1]

    def test_empty_group_retires_with_argument_one(self):
        result, rec, _, _ = run([], finalize_count=0)
        self.assertTrue(result)
        self.assertEqual(rec.events, ['finalize', ('remove_group', CTX, GROUP), ('destroy', GROUP, 1)])

    def test_count_comes_from_group_0x18_after_finalize(self):
        ctx, group, slots, bodies, metadata = build([8, 8], 2, declared=99)
        rec = Recorder(ctx, group, finalize_count=0)
        self.assertTrue(process_pose_group_bytes(
            CTX, GROUP, contexts={CTX: ctx}, groups={GROUP: group}, bodies=bodies,
            metadata=metadata, slot_arrays={SLOTS: slots}, **rec.services()))
        self.assertEqual(rec.events[0], 'finalize')
        self.assertNotIn(('allocate', 16), rec.events)

    def test_single_body_flag_bit3_from_metadata_0x52(self):
        result, rec, ctx, _ = run([0])
        self.assertFalse(result)
        self.assertEqual(rec.events, ['finalize'])
        result, rec, ctx, _ = run([0x08])
        self.assertTrue(result)
        # group410 reloaded from context+0x410 after removal, written by the services
        self.assertEqual(rec.events[2:4], [('remove_body', GROUP, 100), ('append', 57, 100)])
        self.assertEqual(struct.unpack_from('<Q', ctx, 0x410)[0], 57)
        result, rec, _, _ = run([0xf7])  # bit3 clear, other bits set
        self.assertFalse(result)

    def test_single_body_eligibility_uses_low_byte(self):
        result, rec, _, _ = run([8], eligible_result=256)
        self.assertFalse(result)
        self.assertEqual(rec.events, ['finalize', ('eligible', 100)])

    def test_multi_body_destinations_are_written_to_bytes(self):
        result, rec, ctx, _ = run([8, 8], eligible_result=1)
        self.assertTrue(result)
        # eligible() set context+0x410 to 56 before destinations were assigned
        self.assertIn(('migrate', 2, [56, 56]), rec.events)
        self.assertEqual(struct.unpack('<QQ', rec.storage), (56, 56))
        self.assertEqual(rec.events[-3:], ['release', ('remove_group', CTX, GROUP), ('destroy', GROUP, 1)])

    def test_reuse_flag_decides_retirement_and_acquires(self):
        result, rec, _, _ = run([0, 0])
        self.assertFalse(result)
        self.assertIn(('migrate', 2, [GROUP, 77]), rec.events)
        self.assertEqual(rec.events[-1], 'release')
        result, rec, _, _ = run([0, 0], components=1, seeds=[GROUP, GROUP])
        self.assertFalse(result)

    def test_matches_dict_model_for_same_inputs(self):
        for flags in ([8, 0, 8], [0, 0, 0], [8, 8, 8, 8], [0, 8]):
            for elig in (0, 1, 256):
                expected = []
                n = len(flags)
                c = dict(group410=55)
                g = dict(token=GROUP, count=n, slots=[100 + i for i in range(n)])
                bodies = {100 + i: dict(metadata=dict(flags8=flags[i])) for i in range(n)}

                def eligible(cc, b):
                    expected.append(('eligible', b['i'])); cc['group410'] = 56; return elig
                for i in range(n):
                    bodies[100 + i]['i'] = 100 + i
                n_acq = []
                process_pose_group(
                    c, g, bodies=bodies, finalize=lambda c_, g_: None, eligible=eligible,
                    remove_body=lambda g_, b: c.__setitem__('group410', 57),
                    append_body=lambda t, b: False, allocate=lambda k: [0] * (k // 8),
                    prepare=lambda c_, g_, d: 0, acquire_group=lambda c_: 77,
                    migrate=lambda g_, d: expected.append(('migrate', tuple(d['slots']))) or g_.__setitem__('count', 0),
                    release=lambda s: None, remove_group=lambda c_, g_: None,
                    destroy=lambda g_, a: None)
                _, rec, ctx, group = run(flags, eligible_result=elig)
                migrates = [('migrate', tuple(e[2])) for e in rec.events
                            if isinstance(e, tuple) and e[0] == 'migrate']
                self.assertEqual([e for e in expected if e[0] == 'migrate'], migrates)
                self.assertEqual(struct.unpack_from('<Q', ctx, 0x410)[0], c['group410'])
                self.assertEqual(struct.unpack_from('<I', group, 0x18)[0], g['count'])


class CompositionTests(unittest.TestCase):
    def test_rebuild_with_link_removal_and_byte_process(self):
        ctx, group, slots, bodies, metadata = build([8], 1)
        struct.pack_into('<Q', ctx, 0x464, 0xFFFFFFFF_00000007)
        # link array lives at +0x40 (ptr) / +0x48 (count), distinct from the body array
        struct.pack_into('<QI', group, 0x40, 500, 3)
        links = bytearray(struct.pack('<QQQ', 11, 12, 13))
        body = bodies[100]
        struct.pack_into('<Q', body, 0x10, GROUP)
        objects = {}
        for index, token in enumerate((11, 12, 13)):
            obj = bytearray(0x100)
            struct.pack_into('<Q', obj, 8, 100)
            struct.pack_into('<I', obj, 0x80, index)
            objects[token] = obj
        objects[12][0x84] = 2
        groups = {GROUP: group}
        rec = Recorder(ctx, group)
        seen = []
        services = rec.services()
        base_finalize = services['finalize']

        def finalize(c, g):
            seen.append((struct.unpack_from('<I', groups[g], 0x48)[0], groups[g][0xa1]))
            base_finalize(c, g)
        services['finalize'] = finalize
        process = make_pose_group_process(
            contexts={CTX: ctx}, groups=groups, bodies={100: body}, metadata=metadata,
            slot_arrays={SLOTS: slots}, **services)

        def link(group_token, token):
            remove_pose_group_link(groups[group_token], objects[token], objects=objects,
                                   slot_arrays={500: links})

        rebuild_pose_body_connectivity(CTX, [11, 13], contexts={CTX: ctx}, objects=objects,
            bodies={100: body}, groups=groups, link=link, process=process)
        # process ran once, after both link removals, with the a1 mark cleared
        self.assertEqual(seen, [(1, 0)])
        self.assertEqual(struct.unpack_from('<II', ctx, 0x464), (1, 0))
        # count 1 + flags8 bit3 + eligible: body moved, group retired
        self.assertEqual([e[0] if isinstance(e, tuple) else e for e in rec.events],
                         ['finalize', 'eligible', 'remove_body', 'append', 'remove_group', 'destroy'])
        self.assertEqual(struct.unpack_from('<Q', ctx, 0x410)[0], 57)
        for token in (11, 13):
            self.assertEqual(struct.unpack_from('<I', objects[token], 0x80)[0], DETACHED)


if __name__ == '__main__':
    unittest.main()
