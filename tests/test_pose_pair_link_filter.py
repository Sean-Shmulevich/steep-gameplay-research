import struct
import unittest

from engine.pose_pair_link_filter import filter_pose_pair_link
from engine.pose_pair_link_worker import PoseFlatMemory, run_pose_pair_worker
from tests.test_pose_pair_link_worker import A, B, KIND, O, P, Services, world

PROV_PRED, KIND_PRED, BODY_PRED = 0x7100, 0x7200, 0x7300
EXT = 0xB000
LINK = 0xC000


def fixture():
    m = PoseFlatMemory()
    m.add(P, bytearray(0x200))
    m.add(LINK, bytearray(0x90))
    for i, body in enumerate((A, B)):
        m.add(body, bytearray(0x100)); m.add(KIND + i * 0x100, bytearray(0x60))
        m.set_q(body + 0x30, KIND + i * 0x100)
        m.set_q(LINK + 8 + 8 * i, body)
    m.add(EXT, bytearray(0x90))
    return m


class Recorder:
    def __init__(self, results=None):
        self.calls = []; self.results = results or {}

    def __call__(self, address, link):
        self.calls.append((address, link)); return self.results.get(address, 1)


class FilterTests(unittest.TestCase):
    def test_no_predicates_accepts(self):
        r = Recorder()
        self.assertTrue(filter_pose_pair_link(fixture(), P, LINK, invoke=r)); self.assertEqual(r.calls, [])

    def test_call_order_and_link_argument(self):
        m = fixture(); m.set_q(P + 0x188, PROV_PRED)
        m.set_q(KIND + 0x20, EXT); m.set_q(EXT + 0x70, KIND_PRED)
        m.set_q(A + 0xA0, BODY_PRED); m.set_q(B + 0xA0, BODY_PRED + 0x10)
        r = Recorder()
        self.assertTrue(filter_pose_pair_link(m, P, LINK, invoke=r))
        self.assertEqual(r.calls, [(PROV_PRED, LINK), (KIND_PRED, LINK), (BODY_PRED, LINK), (BODY_PRED + 0x10, LINK)])

    def test_equal_pointers_are_called_once(self):
        m = fixture(); m.set_q(KIND + 0x20, EXT); m.set_q(KIND + 0x120, EXT); m.set_q(EXT + 0x70, KIND_PRED)
        m.set_q(A + 0xA0, BODY_PRED); m.set_q(B + 0xA0, BODY_PRED)
        r = Recorder(); filter_pose_pair_link(m, P, LINK, invoke=r)
        self.assertEqual([c[0] for c in r.calls], [KIND_PRED, BODY_PRED])

    def test_first_false_stops_and_only_low_byte_counts(self):
        m = fixture(); m.set_q(P + 0x188, PROV_PRED); m.set_q(A + 0xA0, BODY_PRED)
        r = Recorder({PROV_PRED: 0x100})        # al == 0 despite nonzero rax
        self.assertFalse(filter_pose_pair_link(m, P, LINK, invoke=r)); self.assertEqual(len(r.calls), 1)
        r = Recorder({PROV_PRED: 0xFF00FF})
        self.assertTrue(filter_pose_pair_link(m, P, LINK, invoke=r)); self.assertEqual(len(r.calls), 2)

    def test_second_kind_predicate_runs_when_first_is_null(self):
        m = fixture(); m.set_q(KIND + 0x120, EXT); m.set_q(EXT + 0x70, KIND_PRED)
        r = Recorder(); filter_pose_pair_link(m, P, LINK, invoke=r)
        self.assertEqual(r.calls, [(KIND_PRED, LINK)])

    def test_body_pointer_is_reread_after_a_predicate_edits_the_link(self):
        m = fixture(); m.set_q(P + 0x188, PROV_PRED)
        m.add(0xD000, bytearray(0x100)); m.set_q(0xD000 + 0x30, KIND); m.set_q(0xD000 + 0xA0, BODY_PRED)
        def edit(address, link):
            m.set_q(link + 8, 0xD000); return 1
        r = Recorder()
        def invoke(address, link):
            r.calls.append(address); return edit(address, link)
        filter_pose_pair_link(m, P, LINK, invoke=invoke)
        self.assertEqual(r.calls, [PROV_PRED, BODY_PRED])   # body predicate comes from the replaced first body


class WorkerCompositionTests(unittest.TestCase):
    """The real filter bound as the worker's filter service."""

    def bound(self, kind_result, tree=(), free=(0x11000,)):
        m = world([(A, B, 9)], tree1=tree, free=free, new_cap=1)
        for tree_link in [v for _, v in tree]:
            m.set_q(tree_link + 8, A); m.set_q(tree_link + 0x10, B); m.set_q(tree_link + 0x18, 9)
        m.add(EXT, bytearray(0x90)); m.set_q(KIND + 0x20, EXT); m.set_q(EXT + 0x70, KIND_PRED)
        seen = []
        def invoke(address, link):
            seen.append((address, link, m.q(link + 8), m.q(link + 0x10), m.b(link + 0x84)))
            return kind_result
        s = Services(m)
        s.filter = lambda provider, link: filter_pose_pair_link(m, provider, link, invoke=invoke)
        run_pose_pair_worker(m, O, s)
        return m, s, seen

    def test_rejected_new_link_is_pushed_with_bit1(self):
        m, s, seen = self.bound(0)
        self.assertEqual(seen, [(KIND_PRED, 0x11000, A, B, seen[0][4])])
        self.assertEqual(seen[0][4] & 2, 0)          # bit1 is still clear while the filter runs
        self.assertEqual((m.d(O + 0x10), m.q(0x0A000)), (1, 0x11000))
        self.assertTrue(m.b(0x11084) & 2)

    def test_accepted_new_link_is_pushed_clean(self):
        m, _, _ = self.bound(1)
        self.assertEqual(m.d(O + 0x10), 1); self.assertEqual(m.b(0x11084) & 2, 0)

    def test_rejected_existing_link_loses_bit0_and_is_not_pushed(self):
        m, _, seen = self.bound(0, tree=((9, 0xA0000),))
        self.assertEqual(len(seen), 1)
        self.assertEqual(m.d(O + 0x10), 0)
        self.assertEqual(m.b(0xA0084) & 1, 0)


if __name__ == '__main__':
    unittest.main()
