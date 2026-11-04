import struct
import unittest

from engine.pose_pair_external_contacts import external_pose_contacts
from engine.pose_pair_link_worker import PoseFlatMemory, run_pose_pair_worker
from tests.test_pose_pair_link_worker import A, B, O, PAIRS, Services, world

LINK = 0xC000
REC1, REC2 = 0xE000, 0xE200


def bodies():
    m = PoseFlatMemory({LINK: bytearray(0x90)})
    for body, seed in ((A, 0x10), (B, 0x90)):
        raw = bytearray(0x200)
        for off in range(0x40, 0x7C, 4):
            struct.pack_into('<I', raw, off, seed + off)
        for off in range(0x1A0, 0x1B8, 4):
            struct.pack_into('<I', raw, off, (seed << 8) + off)
        m.add(body, raw)
    m.add(REC1, bytearray(b'\xEE' * 0xD0)); m.add(REC2, bytearray(b'\xEE' * 0xD0))
    return m


class Services2:
    def __init__(self, records, queries=(True, True)):
        self.log = []; self.records = list(records); self.queries = {A: queries[0], B: queries[1]}

    def kwargs(self):
        return dict(guard_enter=lambda: self.log.append('enter'), guard_leave=lambda: self.log.append('leave'),
                    take_record=self.take, query=self.query)

    def take(self):
        self.log.append('take'); return self.records.pop(0)

    def query(self, body, mask):
        self.log.append(('query', body, mask)); return 0x100 if not self.queries[body] else 0xAB01


class ExternalTests(unittest.TestCase):
    def test_new_record_is_taken_inside_the_guard_and_filled(self):
        m = bodies(); s = Services2([REC1])
        external_pose_contacts(m, O, A, B, LINK, **s.kwargs())
        self.assertEqual(s.log, ['enter', 'take', 'leave', ('query', A, 0x8002), ('query', B, 0x8002)])
        self.assertEqual(m.q(LINK + 0x78), REC1)
        for dest, src in ((0x20, 0x40), (0x30, 0x50), (0x40, 0x60), (0x50, 0x70)):
            self.assertEqual(bytes(m.view(REC1 + dest, 12)), bytes(m.view(A + src, 12)))
        for dest, src in ((0x80, 0x40), (0x90, 0x50), (0xA0, 0x60), (0xB0, 0x70)):
            self.assertEqual(bytes(m.view(REC1 + dest, 12)), bytes(m.view(B + src, 12)))
        self.assertEqual(bytes(m.view(REC1, 0x18)), bytes(m.view(A + 0x1A0, 0x18)))
        self.assertEqual(bytes(m.view(REC1 + 0x60, 0x18)), bytes(m.view(B + 0x1A0, 0x18)))

    def test_untouched_record_bytes_survive(self):
        m = bodies(); external_pose_contacts(m, O, A, B, LINK, **Services2([REC1]).kwargs())
        for lo, hi in ((0x18, 0x20), (0x2C, 0x30), (0x3C, 0x40), (0x4C, 0x50), (0x5C, 0x60), (0x78, 0x80), (0x8C, 0x90),
                       (0x9C, 0xA0), (0xAC, 0xB0), (0xBC, 0xD0)):
            self.assertEqual(bytes(m.view(REC1 + lo, hi - lo)), b'\xEE' * (hi - lo), hex(lo))

    def test_false_query_zero_fills_only_its_own_block(self):
        m = bodies(); s = Services2([REC1], queries=(False, True))
        external_pose_contacts(m, O, A, B, LINK, **s.kwargs())
        self.assertEqual(bytes(m.view(REC1, 0x18)), bytes(24))
        self.assertEqual(bytes(m.view(REC1 + 0x60, 0x18)), bytes(m.view(B + 0x1A0, 0x18)))
        m = bodies(); external_pose_contacts(m, O, A, B, LINK, **Services2([REC1], queries=(True, False)).kwargs())
        self.assertEqual(bytes(m.view(REC1 + 0x60, 0x18)), bytes(24))

    def test_existing_record_is_reused_without_guard_or_take(self):
        m = bodies(); m.set_q(LINK + 0x78, REC2); s = Services2([REC1])
        external_pose_contacts(m, O, A, B, LINK, **s.kwargs())
        self.assertEqual(s.log, [('query', A, 0x8002), ('query', B, 0x8002)])
        self.assertEqual(m.q(LINK + 0x78), REC2); self.assertEqual(m.d(REC2 + 0x20), m.d(A + 0x40))
        self.assertEqual(bytes(m.view(REC1, 4)), b'\xEE' * 4)

    def test_only_low_byte_of_query_result_counts(self):
        m = bodies(); s = Services2([REC1], queries=(False, False))
        external_pose_contacts(m, O, A, B, LINK, **s.kwargs())
        self.assertEqual(bytes(m.view(REC1, 0x18)) + bytes(m.view(REC1 + 0x60, 0x18)), bytes(48))


class WorkerCompositionTests(unittest.TestCase):
    """The real external-contacts routine bound as the worker's service."""

    def run_worker(self, tree=(), held=0, free=(0x11000,)):
        m = world([(A, B, 9)], tree1=tree, free=free, new_cap=1, aa=(0, 0x80))
        for body in (A, B):                      # extend the synthetic bodies past +0x1A0
            old = bytes(m.regions[body]); m.add(body, bytearray(old) + bytearray(0x100))
            for off in range(0x40, 0x7C, 4):
                m.set_d(body + off, body + off)
        m.add(REC1, bytearray(0xD0))
        for _, link in tree:
            m.set_q(link + 8, A); m.set_q(link + 0x10, B); m.set_q(link + 0x78, held)
        s = Services(m); q = Services2([REC1])
        s.external_contacts = lambda owner, a, b, link: (s.log.append(('external', link)),
                                                          external_pose_contacts(m, owner, a, b, link, **q.kwargs()))
        run_pose_pair_worker(m, O, s)
        return m, s, q

    def test_new_link_gets_a_snapshot_record(self):
        m, s, q = self.run_worker()
        self.assertEqual(m.q(0x11000 + 0x78), REC1)
        self.assertEqual(q.log[:3], ['enter', 'take', 'leave'])
        self.assertEqual(m.d(REC1 + 0x20), m.d(A + 0x40)); self.assertEqual(m.d(REC1 + 0x80), m.d(B + 0x40))
        self.assertNotIn('held', [e[0] for e in s.log])

    def test_existing_link_with_record_is_refilled_in_place(self):
        m, s, q = self.run_worker(tree=((9, 0xA0000),), held=REC1)
        self.assertEqual(m.q(0xA0000 + 0x78), REC1)
        self.assertEqual([e for e in q.log if e in ('enter', 'take', 'leave')], [])
        self.assertEqual(m.d(REC1 + 0x50), m.d(A + 0x70))
        self.assertNotIn('held', [e[0] for e in s.log])

    def test_existing_link_without_record_takes_one(self):
        m, _, q = self.run_worker(tree=((9, 0xA0000),), held=0)
        self.assertEqual(m.q(0xA0000 + 0x78), REC1); self.assertIn('take', q.log)


if __name__ == '__main__':
    unittest.main()
