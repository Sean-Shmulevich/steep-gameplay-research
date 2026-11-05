import random
import struct
import unittest

from engine.pose_pair_link_worker import PoseFlatMemory
from engine.pose_contact_payload_update import (
    update_pose_contact_payload, bind_pose_contact_payload_update, transform_pose_contact_point, XYZ_MASK)
from engine.pose_link_update import update_pose_link_payload
from engine.pose_pair_contact_generation import generate_pose_pair_contacts, lookup_pose_link_payload

try:
    from tests.test_pose_pair_contact_generation import world, Services, O, A, B, LINK, SCR
except ImportError:
    from test_pose_pair_contact_generation import world, Services, O, A, B, LINK, SCR

# Authored synthetic layout.
PL, PAIR, B1, B2, REC = 0x1000, 0x2000, 0x3000, 0x3400, 0x4000


def bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def body(basis, t, w=123.0):
    raw = bytearray(0x100)
    for r, v in enumerate(list(basis) + [t]):
        struct.pack_into('<4f', raw, 0x40 + 16 * r, *v, w)
    return raw


def record(p1, p2, feature, w2=8.0, head=b'\x11' * 16):
    return head + struct.pack('<3fI3ff', *p1, feature, *p2, w2)


IDENT = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def memory(payload, records, b1=None, b2=None, i=2, j=3):
    m = PoseFlatMemory({PL: bytearray(payload), REC: bytearray(b''.join(records) or bytes(48)),
                        B1: b1 or body(IDENT, (1, 2, 3)), B2: b2 or body(IDENT, (-1, -1, -1))})
    return m, struct.pack('<QQHH', B1, B2, i, j)


class LayoutTests(unittest.TestCase):
    def test_row_fields_tail_and_untouched_rows(self):
        p = bytearray([0xA5]) * 0x120
        struct.pack_into('<I', p, 0x110, 0)
        m, pair = memory(p, [record((4, 6, 8), (9, 10, 11), 5)])
        update_pose_contact_payload(m, PL, pair, REC, 1)
        out = bytes(m.view(PL, 0x120))
        self.assertEqual(out[0x10:0x20], b'\x11' * 16)
        self.assertEqual(struct.unpack_from('<3fI', out, 0x20), (3, 4, 5, 5))        # point-t, w word = feature
        self.assertEqual(struct.unpack_from('<4f', out, 0x30), (10, 11, 12, 8))      # second body, record w kept
        self.assertEqual(struct.unpack_from('<IIHH', out, 0x40), (0, 0, 2, 3))
        self.assertEqual(out[0x4C:0x50], p[0x4C:0x50])
        self.assertEqual(out[0x50:0x110], p[0x50:0x110])
        self.assertEqual(struct.unpack_from('<I', out, 0x110)[0], 1)
        self.assertEqual(out[0x114:], p[0x114:])

    def test_body_w_lanes_are_masked_out(self):
        b1 = body(IDENT, (0, 0, 0), w=float('nan'))
        m, pair = memory(bytes(0x120), [record((1, 2, 3), (0, 0, 0), 0)], b1=b1)
        update_pose_contact_payload(m, PL, pair, REC, 1)
        self.assertEqual(struct.unpack_from('<3f', bytes(m.view(PL + 0x20, 12))), (1, 2, 3))

    def test_zero_count_only_writes_count(self):
        p = bytearray(range(256)) + bytearray(0x20)
        m, pair = memory(p, [])
        update_pose_contact_payload(m, PL, pair, REC, 0)
        p[0x110:0x114] = bytes(4)
        self.assertEqual(bytes(m.view(PL, 0x120)), bytes(p))

    def test_no_four_record_bound_and_count_written_last(self):
        p = bytearray(0x10 + 0x40 * 6)
        recs = [record((k, 0, 0), (0, 0, 0), 0) for k in range(5)]
        m, pair = memory(p, recs)
        update_pose_contact_payload(m, PL, pair, REC, 5)
        # row 4 starts at +0x110 and overwrites the count field before the final store
        self.assertEqual(bytes(m.view(PL + 0x110, 16)), struct.pack('<I', 5) + b'\x11' * 12)
        self.assertEqual(struct.unpack_from('<f', bytes(m.view(PL + 0x120, 4)))[0], 3.0)


class CacheTests(unittest.TestCase):
    def payload(self, ids, words, old):
        p = bytearray(0x120)
        for k in range(4):
            struct.pack_into('<I', p, 0x2C + 0x40 * k, ids[k])
            struct.pack_into('<I', p, 0x40 + 0x40 * k, words[k])
        struct.pack_into('<I', p, 0x110, old)
        return p

    def run_update(self, p, features):
        m, pair = memory(p, [record((0, 0, 0), (0, 0, 0), f) for f in features])
        update_pose_contact_payload(m, PL, pair, REC, len(features))
        return [m.d(PL + 0x40 + 0x40 * i) for i in range(len(features))]

    def test_lowest_matching_old_row_wins_from_entry_snapshot(self):
        p = self.payload((7, 7, 9, 7), (10, 11, 12, 13), 4)
        # row 0 is rewritten with feature 1 before record 1 looks up 7: snapshot still used
        self.assertEqual(self.run_update(p, (1, 7, 9, 5)), [0, 10, 12, 0])

    def test_cached_words_gated_by_unsigned_old_count(self):
        p = self.payload((1, 2, 3, 4), (10, 11, 12, 13), 2)
        self.assertEqual(self.run_update(p, (1, 2, 3, 4)), [10, 11, 0, 0])
        p = self.payload((1, 2, 3, 4), (10, 11, 12, 13), 0xFFFFFFFF)
        self.assertEqual(self.run_update(p, (4, 3, 2, 1)), [13, 12, 11, 10])


class FloatTests(unittest.TestCase):
    def rows(self, basis, t):
        return [[bits(x) for x in r] + [0] for r in basis] + [[bits(x) for x in t] + [0]]

    def test_matches_dict_model_on_finite_inputs(self):
        rng = random.Random(5)
        for _ in range(64):
            fr = [[[rng.uniform(-3, 3) for _ in range(3)] for _ in range(4)] for _ in range(2)]
            p = bytearray(rng.randbytes(0x120))
            struct.pack_into('<I', p, 0x110, rng.choice([0, 2, 4, 0xFFFFFFFF]))
            for k in range(4):
                struct.pack_into('<I', p, 0x2C + 0x40 * k, rng.randrange(4))
            recs = [rng.randbytes(16) + struct.pack('<3fI3fI', *[rng.uniform(-100, 100) for _ in range(3)],
                                                    rng.randrange(4), *[rng.uniform(-100, 100) for _ in range(3)], 9)
                    for _ in range(rng.randrange(5))]
            m, pair = memory(p, recs, body(fr[0][:3], fr[0][3]), body(fr[1][:3], fr[1][3]), 0x1234, 0xFEDC)
            update_pose_contact_payload(m, PL, pair, REC, len(recs))
            f32 = lambda v: [struct.unpack('<f', struct.pack('<f', x))[0] for x in v]
            expected = update_pose_link_payload(
                bytes(p), recs, first_frame=dict(basis=[f32(r) for r in fr[0][:3]], translation=f32(fr[0][3])),
                second_frame=dict(basis=[f32(r) for r in fr[1][:3]], translation=f32(fr[1][3])),
                first_index=0x1234, second_index=0xFEDC)
            self.assertEqual(bytes(m.view(PL, 0x120)), expected)

    def test_hadd_tree_keeps_pair_sums(self):
        # (x + y) + (z + w); visible only when the w lane is not zero (non-XYZ mask)
        big = 16777216.0
        rows = [[bits(1.0)] * 4, [0] * 4, [0] * 4, [0] * 4]
        out = transform_pose_contact_point(rows, [bits(big), bits(1.0), bits(1.0), bits(1.0)])
        self.assertEqual(out[0], bits(big + 2))           # left to right would round to big
        # signed zero under the XYZ mask: (-0 + -0) + (-0 + +0) = +0
        rows = self.rows(((1, 1, 1), (0, 0, 0), (0, 0, 0)), (0, 0, 0))
        out = transform_pose_contact_point(rows, [bits(-0.0)] * 3 + [0])
        self.assertEqual(out[0], 0)
        self.assertEqual(out[3], out[2])                  # fourth lane duplicates the third

    def test_nan_rules(self):
        snan, qnan, neg_q = 0x7F800001, 0x7FC00005, 0xFFC00009
        rows = self.rows(((1, 0, 0), (0, 0, 0), (0, 0, 0)), (0, 0, 0))
        # single SNaN in the point is quieted and carried through the products and sums
        self.assertEqual(transform_pose_contact_point(rows, [snan, 0, 0, 0])[0], 0x7FC00001)
        # inf - inf is invalid: default NaN
        rows_inf = self.rows(((1, 0, 0), (0, 0, 0), (0, 0, 0)), (float('inf'), 0, 0))
        self.assertEqual(transform_pose_contact_point(rows_inf, [bits(float('inf')), 0, 0, 0])[0], 0xFFC00000)
        # two NaNs: row lane (first operand) vs difference lane
        rows_nan = [[neg_q, 0, 0, 0], [0] * 4, [0] * 4, [0] * 4]
        self.assertEqual(transform_pose_contact_point(rows_nan, [qnan, 0, 0, 0], 'sse')[0], neg_q)
        self.assertEqual(transform_pose_contact_point(rows_nan, [qnan, 0, 0, 0], 'x87')[0], neg_q)   # larger fraction
        rows_nan = [[0x7FC00001, 0, 0, 0], [0] * 4, [0] * 4, [0] * 4]
        self.assertEqual(transform_pose_contact_point(rows_nan, [qnan, 0, 0, 0], 'sse')[0], 0x7FC00001)
        self.assertEqual(transform_pose_contact_point(rows_nan, [qnan, 0, 0, 0], 'x87')[0], qnan)


class CompositionTests(unittest.TestCase):
    def test_bound_into_pair_contact_generation(self):
        m = world(pool=(0x9000,))
        m.add(0x9000, bytearray(0x120))
        m.add(SCR, bytearray(0x30 * 4))
        struct.pack_into('<3fI3fI', m.regions[SCR], 0x10, 5, 6, 7, 42, 1, 1, 1, 0)
        struct.pack_into('<3fI3fI', m.regions[SCR], 0x40, 2, 2, 2, 43, 3, 3, 3, 0)
        m.regions[A][0x70:0x7C] = struct.pack('<3f', 1, 1, 1)       # first body translation
        s = Services(m, counts=[2])
        s.update_payload = bind_pose_contact_payload_update(m)
        generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
        self.assertEqual(lookup_pose_link_payload(m, LINK, 0, 0), 0x9000)
        self.assertEqual(m.d(0x9000 + 0x110), 2)
        self.assertEqual(struct.unpack('<3fI', bytes(m.view(0x9000 + 0x20, 16))), (4, 5, 6, 42))
        self.assertEqual(struct.unpack('<3f', bytes(m.view(0x9000 + 0x30, 12))), (1, 1, 1))
        self.assertEqual(struct.unpack('<3f', bytes(m.view(0x9000 + 0x60, 12))), (1, 1, 1))
        self.assertEqual(struct.unpack('<IIHH', bytes(m.view(0x9000 + 0x40, 12))), (0, 0, 0, 0))
        self.assertEqual(m.b(0x9000 + 0x114) & 1, 1)

    def test_second_pass_reuses_cached_word_by_feature(self):
        m = world(pool=(0x9000,))
        m.add(0x9000, bytearray(0x120))
        m.add(SCR, bytearray(0x30 * 4))
        struct.pack_into('<I', m.regions[SCR], 0x1C, 42)
        s = Services(m, counts=[1, 1])
        s.update_payload = bind_pose_contact_payload_update(m)
        generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
        m.set_d(0x9000 + 0x40, 0xCAFE)                    # downstream writes the row's cached word
        generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
        self.assertEqual(m.d(0x9000 + 0x40), 0xCAFE)       # same feature id 42 -> word carried
        struct.pack_into('<I', m.regions[SCR], 0x1C, 41)
        s.counts = [1]
        generate_pose_pair_contacts(m, O, A, B, LINK, False, s)
        self.assertEqual(m.d(0x9000 + 0x40), 0)


if __name__ == '__main__':
    unittest.main()
