import random
import struct
import unittest
from types import SimpleNamespace

from engine.pose_pair_link_worker import PoseFlatMemory, process_pose_dynamic_pair
from engine.pose_pair_contact_generation import (
    generate_pose_pair_contacts, compose_pose_entry_frame, lookup_pose_link_payload,
    remove_pose_link_entry, clear_pose_link_pair, acquire_pose_contact_payload,
    release_pose_contact_payload, insert_pose_link_payload, reserve_pose_link_entries)
from engine.pose_link_record import remove_link_key
from engine.pose_contact_cache import clear_contact_pair

# Authored synthetic layout (addresses are fixture choices, not engine addresses).
P, O, A, B, KA, KB, EA, EB, LOC, SH, SD, LINK, LARR, PL, POOL, SCR, DISP = (
    0x1000, 0x2000, 0x3000, 0x3400, 0x3800, 0x3900, 0x4000, 0x4400, 0x5000, 0x6000, 0x6800,
    0x7000, 0x7100, 0x8000, 0xA000, 0xB000, 0xC000)
ONES = (1 << 64) - 1
IDENT = struct.pack('<16f', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)


def frame(t=(0, 0, 0)):
    return struct.pack('<16f', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, t[0], t[1], t[2], 1)


class Services:
    """Authored recording stand-ins for the supplied services."""
    def __init__(self, mem, counts=(), update_count=None, boxes=None):
        self.mem = mem; self.log = []; self.counts = list(counts); self.update_count = update_count
        self.boxes = boxes or {}; self.heap = 0x20000; self.fresh = 0x40000
    @property
    def allocator(self): return self
    def allocate(self, size, align, tag):
        p = self.heap; self.heap += 0x1000; self.mem.add(p, bytearray(size)); self.log.append(('allocate', size, align, tag)); return p
    def reallocate(self, old, size, align, tag):
        p = self.heap; self.heap += 0x1000; src = bytes(self.mem.regions[old][:size])
        self.mem.add(p, bytearray(src) + bytearray(size - len(src))); self.log.append(('reallocate', old, size, tag)); return p
    def release(self, p): self.log.append(('release', p))
    def shape_bounds(self, shape, frame64):
        self.log.append(('bounds', shape)); return struct.pack('<6f', *self.boxes.get(shape, (-1, -1, -1, 1, 1, 1)))
    def lookup_handler(self, dispatcher, a, b): self.log.append(('lookup', dispatcher, a, b)); return 0x77
    def produce_contacts(self, handler, descriptor, scratch, capacity):
        self.log.append(('produce', handler, len(descriptor), scratch, capacity)); self.descriptor = descriptor
        return self.counts.pop(0) if self.counts else 0
    def update_payload(self, payload, pair, scratch, count):
        self.log.append(('update', payload, struct.unpack('<QQHH', pair), count))
        self.mem.set_d(payload + 0x110, count if self.update_count is None else self.update_count)
    def terrain_narrow(self, owner, descriptor, pair, link): self.log.append(('narrow', struct.unpack('<QQHH', pair)))
    def terrain_wide(self, owner, descriptor, pair, link): self.log.append(('wide', struct.unpack('<QQHH', pair)))
    def refill_payloads(self, dest, n):
        self.log.append(('refill', dest, n))
        for i in range(n):
            p = self.fresh; self.fresh += 0x120; self.mem.add(p, bytearray(0x118)); self.mem.set_q(dest + 8 * i, p)


def world(na=1, nb=1, kinds=(1, 1), flags=0x1C, masks=ONES, link_entries=(), pool=(), pool_cap=4,
          aa=(0, 0), b52=0, kind_bounds=(-10, -10, -10, 10, 10, 10)):
    m = PoseFlatMemory()
    m.add(P, bytearray(0x100)); m.put('<Q', P + 0x68, DISP)
    m.add(O, bytearray(0x80)); m.set_q(O, P); m.set_q(O + 0x58, SCR)
    m.add(SCR, bytearray(16))
    shapes = 0
    for body, kind, ents, n, off, flag in ((A, KA, EA, na, 0, aa[0]), (B, KB, EB, nb, 8, aa[1])):
        b = m.add(body, bytearray(0x100)); b[0x40:0x80] = IDENT; b[0xAA] = flag
        struct.pack_into('<Q', b, 0x30, kind); struct.pack_into('<Q', b, 0xB8, ents); struct.pack_into('<H', b, 0xC0, n)
        k = m.add(kind, bytearray(0x60)); struct.pack_into('<6f', k, 4, *kind_bounds); k[0x52] = b52
        e = m.add(ents, bytearray(max(n, 1) * 0x48))
        for i in range(n):
            shape, data, loc = SH + (off + i) * 0x40, SD + (off + i) * 0x60, LOC + (off + i) * 0x40
            m.add(loc, bytearray(frame((off + i, 0, 0))))
            struct.pack_into('<QQ', e, i * 0x48 + 0x10, shape, loc)
            struct.pack_into('<QQII', e, i * 0x48 + 0x28, masks, masks, 0xFFFFFFFF, 0xFFFFFFFF)
            e[i * 0x48 + 0x44] = flags
            s = m.add(shape, bytearray(0x40)); struct.pack_into('<Q', s, 0x20, data)
            struct.pack_into('<H', s, 0x28, kinds[0] if body == A else kinds[1])
            d = m.add(data, bytearray(0x60)); struct.pack_into('<QQ', d, 0x48, ONES, ONES)
    link = m.add(LINK, bytearray(0x90))
    m.add(LARR, bytearray(16 * 8))
    struct.pack_into('<QII', link, 0x58, LARR, 0, 8)
    for i, (first, second, detail) in enumerate(link_entries):
        payload = PL + i * 0x120; m.add(payload, bytearray(0x118)); m.set_d(payload + 0x110, 3)
        struct.pack_into('<HHIQ', m.regions[LARR], i * 16, first, second, detail, payload)
    m.set_d(LINK + 0x60, len(link_entries))
    m.add(POOL, bytearray(max(pool_cap, 1) * 8))
    struct.pack_into('<QII', m.regions[O], 0x38, POOL if pool_cap else 0, len(pool), pool_cap)
    for i, payload in enumerate(pool):
        m.add(payload, bytearray(0x118)); m.set_q(POOL + 8 * i, payload)
    return m


class FrameTests(unittest.TestCase):
    def test_translation_composes_through_body_rows_and_w_is_masked(self):
        m = PoseFlatMemory({0: bytearray(struct.pack('<16f', 0, 1, 0, 9, -1, 0, 0, 9, 0, 0, 2, 9, 5, 6, 7, 9)),
                            0x100: bytearray(struct.pack('<16f', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 2, 3, 0))})
        out = struct.unpack('<16f', compose_pose_entry_frame(m, 0, 0x100))
        self.assertEqual(out[0:4], (0, 1, 0, 0))
        self.assertEqual(out[12:15], (5 - 2, 6 + 1, 7 + 6))
        self.assertEqual(out[15], 0)

    def test_float32_add_order_of_translation_row(self):
        # ((A0*x + A3) + A1*y) + A2*z differs from (A0*x + A1*y + A2*z) + A3 here.
        big = 16777216.0
        m = PoseFlatMemory({0: bytearray(struct.pack('<16f', 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, -big, 0, 0, 0)),
                            0x100: bytearray(struct.pack('<16f', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, big, 1, 1, 0))})
        out = struct.unpack('<16f', compose_pose_entry_frame(m, 0, 0x100))
        self.assertEqual(out[12], 2.0)        # ((big - big) + 1) + 1; adding A3 last would give 0


class GateTests(unittest.TestCase):
    def test_single_pair_new_payload_from_pool_is_inserted_and_updated(self):
        m = world(pool=(0x9000,)); s = Services(m, counts=[3])
        generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
        self.assertEqual([e[0] for e in s.log], ['lookup', 'produce', 'update'])  # no bounds with one entry each
        self.assertEqual(s.log[1][1:], (0x77, 0x93, SCR, 500))
        self.assertEqual(s.log[2], ('update', 0x9000, (A, B, 0, 0), 3))
        self.assertEqual(lookup_pose_link_payload(m, LINK, 0, 0), 0x9000)
        self.assertEqual(m.q(0x9000), LINK)                       # payload owner
        self.assertEqual(m.b(0x9000 + 0x114) & 1, 1)              # bits 2 and 4 set in 0x1c
        self.assertEqual(m.d(O + 0x40), 0)
        tail = s.descriptor[0x80:]
        self.assertEqual(struct.unpack('<QQ3B', tail), (SH, SH + 8 * 0x40, 1, 0, 1))

    def test_contact_bit_needs_bit4_on_both_entries(self):
        m = world(flags=0x0C, pool=(0x9000,)); s = Services(m, counts=[1])
        m.set_b(0x9000 + 0x114, 0xFF)
        generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
        self.assertEqual(m.b(0x9000 + 0x114), 0xFE)

    def test_inactive_entries_and_null_shapes_are_skipped_without_clear(self):
        for flags in (0x04, 0x08, 0x14):
            m = world(flags=flags, link_entries=[(0, 0, 0)]); s = Services(m)
            generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
            self.assertEqual(s.log, []); self.assertEqual(m.d(LINK + 0x60), 1)

    def test_mask_miss_clears_pair_into_pool_ignoring_detail(self):
        m = world(masks=0, link_entries=[(0, 0, 5), (1, 0, 0), (0, 0, 0)]); s = Services(m)
        generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
        self.assertEqual(m.d(LINK + 0x60), 1)
        self.assertEqual(m.d(O + 0x40), 2)
        self.assertEqual([m.q(POOL), m.q(POOL + 8)], [PL + 2 * 0x120, PL])     # last match first
        self.assertEqual(m.d(PL + 0x110), 0)

    def test_same_group_selects_32bit_masks_and_both_with_flag_clear(self):
        m = world(); struct.pack_into('<II', m.regions[EA], 0x38, 0, 0)
        s = Services(m); generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
        self.assertEqual(s.log[0][0], 'lookup')             # different groups: only 64-bit masks
        s = Services(m); generate_pose_pair_contacts(m, O, A, B, LINK, True, s)
        self.assertEqual(s.log, [])                         # same group, b52 clear: both required
        m = world(b52=0x10); struct.pack_into('<QQ', m.regions[EA], 0x28, 0, 0)
        s = Services(m); generate_pose_pair_contacts(m, O, A, B, LINK, True, s)
        self.assertEqual(s.log[0][0], 'lookup')             # b52 bit 0x10: only 32-bit masks

    def test_terrain_routing(self):
        for kinds, expect in (((7, 7), []), ((6, 0x8007), []), ((6, 1), ['narrow']), ((1, 0x8006), ['narrow']),
                              ((7, 1), ['wide']), ((2, 0x8007), ['wide']), ((2, 0x7FF7), ['lookup', 'produce'])):
            m = world(kinds=kinds, link_entries=[(0, 0, 0)]); s = Services(m)
            generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
            self.assertEqual([e[0] for e in s.log], expect, kinds)
            if expect != ['lookup', 'produce']:
                self.assertEqual(m.d(LINK + 0x60), 1)        # terrain paths never clear here

    def test_first_bounds_against_second_kind_record_clear_whole_row(self):
        m = world(na=2, nb=3, link_entries=[(0, 0, 0), (0, 2, 0), (1, 1, 0)], kind_bounds=(5, 5, 5, 6, 6, 6))
        s = Services(m); generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
        self.assertEqual([e for e in s.log], [('bounds', SH), ('bounds', SH + 0x40)])
        self.assertEqual(m.d(LINK + 0x60), 0)

    def test_unordered_min_passes_but_unordered_max_rejects(self):
        nan = float('nan')
        m = world(na=2, nb=1); s = Services(m, boxes={SH: (nan, -1, -1, 1, 1, 1), SH + 0x40: (-1, -1, -1, nan, 1, 1)})
        generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
        self.assertEqual([e[0] for e in s.log], ['bounds', 'lookup', 'produce', 'bounds'])

    def test_second_bounds_only_with_several_second_entries(self):
        m = world(na=1, nb=2, link_entries=[(0, 1, 0)])
        s = Services(m, boxes={SH + 9 * 0x40: (4, 4, 4, 5, 5, 5)})
        generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
        self.assertEqual([e[0] for e in s.log], ['bounds', 'bounds', 'lookup', 'produce', 'bounds'])
        self.assertEqual(m.d(LINK + 0x60), 0)                  # (0,1) cleared by the box test

    def test_zero_count_resets_existing_and_releases_it(self):
        m = world(link_entries=[(0, 0, 0)], pool_cap=0); s = Services(m, counts=[0])
        generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
        self.assertEqual(m.d(LINK + 0x60), 0); self.assertEqual(m.d(PL + 0x110), 0)
        self.assertEqual(s.log[-1], ('allocate', 64, 0x10, 0x28))
        self.assertEqual((m.d(O + 0x40), m.d(O + 0x44), m.q(m.q(O + 0x38))), (1, 8, PL))

    def test_update_to_zero_removes_and_releases(self):
        m = world(link_entries=[(0, 0, 0)]); s = Services(m, counts=[4], update_count=0)
        generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
        self.assertEqual(s.log[-1], ('update', PL, (A, B, 0, 0), 4))
        self.assertEqual(m.d(LINK + 0x60), 0); self.assertEqual(m.q(POOL), PL)

    def test_empty_pool_refills_ten_and_inline_entries_grow(self):
        m = world(pool_cap=0); s = Services(m, counts=[1])
        struct.pack_into('<QII', m.regions[LINK], 0x58, LINK + 0x68, 1, 1)
        struct.pack_into('<HHIQ', m.regions[LINK], 0x68, 9, 9, 0, 0xDEAD)
        generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
        names = [e[0] for e in s.log]
        self.assertEqual(names, ['lookup', 'produce', 'allocate', 'refill', 'allocate', 'update'])
        self.assertEqual(s.log[2], ('allocate', 80, 0x10, 0x28)); self.assertEqual(s.log[4], ('allocate', 32, 0x10, 0x2D))
        self.assertEqual(m.d(O + 0x40), 9)
        new = m.q(LINK + 0x58)
        self.assertEqual(struct.unpack('<HHIQ', bytes(m.view(new, 16))), (9, 9, 0, 0xDEAD))
        self.assertEqual(m.d(LINK + 0x64), 2)


class LeafEquivalenceTests(unittest.TestCase):
    def test_flat_remove_and_clear_match_dict_reconstructions(self):
        r = random.Random(4)
        for _ in range(200):
            n = r.randrange(8)
            rows = [struct.pack('<HHIQ', r.randrange(3), r.randrange(3), r.choice((0, 0, 7)),
                                0 if r.random() < 0.1 else 0x100 + 0x200 * i) for i in range(n)]
            first, second, detail = r.randrange(3), r.randrange(3), r.choice((0, 7))
            m = PoseFlatMemory({LINK: bytearray(0x90), LARR: bytearray(b''.join(rows) + bytes(16)),
                                POOL: bytearray(64), O: bytearray(0x80)})
            struct.pack_into('<QII', m.regions[LINK], 0x58, LARR, n, 8)
            for i in range(n): m.add(0x100 + 0x200 * i + 0x100000, bytearray(0x118))
            c = {'count': n, 'slots': list(rows)}
            remove_link_key(c, first, second, detail); remove_pose_link_entry(m, LINK, first, second, detail)
            self.assertEqual(m.d(LINK + 0x60), c['count'])
            self.assertEqual(bytes(m.view(LARR, 16 * c['count'])), b''.join(c['slots'][:c['count']]))
            # clear: payload identities point into flat memory offset by 0x100000 for the dict model
            pay = {}
            for row in c['slots'][:c['count']]:
                ident = struct.unpack_from('<Q', row, 8)[0]
                if ident: pay[ident] = bytearray(0x118)
            for i, row in enumerate(c['slots'][:c['count']]):
                ident = struct.unpack_from('<Q', row, 8)[0]
                if ident: m.add(ident, bytearray(0x118))
            rec = {'count': 0, 'capacity': 0, 'slots': []}
            clear_contact_pair(c, first, second, rec, payloads=pay)
            struct.pack_into('<QII', m.regions[O], 0x38, 0, 0, 0)
            s = Services(m); clear_pose_link_pair(m, LINK, first, second, O + 0x28, allocator=s)
            self.assertEqual(m.d(LINK + 0x60), c['count'])
            self.assertEqual(bytes(m.view(LARR, 16 * c['count'])), b''.join(c['slots'][:c['count']]))
            self.assertEqual([m.q(m.q(O + 0x38) + 8 * i) for i in range(m.d(O + 0x40))], rec['slots'][:rec['count']])

    def test_release_and_acquire_are_lifo(self):
        m = world(pool=(0x9000, 0x9200)); s = Services(m)
        m.add(0xD000, bytearray(0x118)); m.set_d(0xD000 + 0x110, 9)
        release_pose_contact_payload(m, O + 0x28, 0xD000, allocator=s)
        self.assertEqual(m.d(0xD000 + 0x110), 0)
        self.assertEqual(acquire_pose_contact_payload(m, O + 0x28, allocator=s, refill=s.refill_payloads), 0xD000)
        self.assertEqual(acquire_pose_contact_payload(m, O + 0x28, allocator=s, refill=s.refill_payloads), 0x9200)

    def test_entry_reserve_shrinks_back_to_inline(self):
        m = PoseFlatMemory({LINK: bytearray(0x90), P: bytearray(0x118)}); s = Services(m)
        struct.pack_into('<QII', m.regions[LINK], 0x58, LINK + 0x68, 0, 1)
        for i in range(3): insert_pose_link_payload(m, LINK, i, i, 0, P, allocator=s)
        self.assertEqual((m.d(LINK + 0x60), m.d(LINK + 0x64)), (3, 4))
        heap = m.q(LINK + 0x58)
        reserve_pose_link_entries(m, LINK + 0x58, 1, allocator=s)
        self.assertEqual(s.log[-1], ('release', heap))
        self.assertEqual((m.q(LINK + 0x58), m.d(LINK + 0x60), m.d(LINK + 0x64)), (LINK + 0x68, 1, 1))
        self.assertEqual(m.w(LINK + 0x68), 0)


class WorkerCompositionTests(unittest.TestCase):
    def test_bound_into_dynamic_pair_handler(self):
        """process_pose_dynamic_pair -> generate_pose_pair_contacts over one flat memory."""
        m = world(na=2, nb=1, link_entries=[(1, 0, 0)], pool=(0x9000,))
        # provider tree at +8 holds the pair key -> existing link
        m.add(0xE000, bytearray(32)); struct.pack_into('<iiiBBxxQQ', m.regions[0xE000], 0, -1, -1, -1, 0, 0, LINK, 0x55)
        m.set_q(P + 8, 0xE000); m.put('<i', P + 0x1C, 0)
        m.add(0xF000, bytearray(struct.pack('<QQQ', A, B, 0x55)))
        m.set_q(KA + 0x20, 1); m.set_q(KB + 0x20, 2)
        s = Services(m, counts=[2, 0])
        calls = []
        worker = SimpleNamespace(
            generate_contacts=lambda owner, a, b, link, same: (calls.append(same),
                                                               generate_pose_pair_contacts(m, owner, a, b, link, same, s)),
            refresh_contact_flag=lambda link: calls.append('flag'),
            release_held=lambda link: calls.append('held'),
            external_contacts=lambda *a: calls.append('external'),
            filter=lambda provider, link: True)
        process_pose_dynamic_pair(m, O, 0xF000, worker)
        self.assertEqual(calls, [False, 'flag'])
        self.assertEqual([e[0] for e in s.log], ['bounds', 'lookup', 'produce', 'update', 'bounds', 'lookup', 'produce'])
        self.assertEqual(s.log[3], ('update', 0x9000, (A, B, 0, 0), 2))
        # entry (1,0) produced nothing: reset and returned to the pool; (0,0) inserted
        self.assertEqual(lookup_pose_link_payload(m, LINK, 0, 0), 0x9000)
        self.assertEqual(lookup_pose_link_payload(m, LINK, 1, 0), 0)
        self.assertEqual((m.d(O + 0x40), m.q(POOL)), (1, PL))
        self.assertEqual(m.d(O + 0x10), 0)        # found link: never pushed


if __name__ == '__main__':
    unittest.main()
