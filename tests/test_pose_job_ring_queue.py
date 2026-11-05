import struct
import unittest
from engine import pose_job_ring_queue as Q
from engine.pose_dispatch import dispatch_pose_workers, pose_dispatch_serial_atomics
from engine.pose_job_ring_model_check import explore, make_record as rec


def queue():
    return bytearray(Q.QUEUE_BYTES)


def counters(buf, base=0):
    return struct.unpack_from('<4I', buf, base + 0x400)


class SequentialTests(unittest.TestCase):
    """Recovered sequential behavior (natively validated by the Unicorn harness)."""

    def test_fifo_and_counters(self):
        q = queue()
        for n in range(5):
            Q.push_record(q, rec(n))
        self.assertEqual(counters(q), (0, 0, 120, 120))
        self.assertEqual([Q.pop_record(q) for _ in range(5)], [rec(n) for n in range(5)])
        self.assertEqual(counters(q), (120, 120, 120, 120))
        self.assertIsNone(Q.pop_record(q))

    def test_record_splits_across_ring_end(self):
        q = queue()
        for n in range(42):                  # 1008 bytes, 16 left: record 43 would not fit
            Q.push_record(q, rec(n))
        with self.assertRaises(Q.RingStalled):
            Q.push_record(q, rec(99), spin_limit=200)
        self.assertEqual(Q.pop_record(q), rec(0))
        Q.push_record(q, rec(42))            # starts at ring offset 1008, wraps 16+8
        self.assertEqual(bytes(q[1008:1024]), rec(42)[:16])
        self.assertEqual(bytes(q[0:8]), rec(42)[16:])

    def test_counter_wrap(self):
        q = queue()
        struct.pack_into('<4I', q, 0x400, *([0xffffffe8] * 4))
        Q.push_record(q, rec(1))
        Q.push_record(q, rec(2))
        self.assertEqual(counters(q)[2], (0xffffffe8 + 48) & 0xffffffff)
        self.assertEqual(Q.pop_record(q), rec(1))
        self.assertEqual(Q.pop_record(q), rec(2))

    def test_unpublished_writer_hides_record_and_blocks_publication(self):
        q = queue()
        a, b = Q.PushOp(rec(1)), Q.PushOp(rec(2))
        for name in ('load_read_published', 'load_write_claim', 'claim_cas', 'copy_head'):
            self.assertEqual(a.step(q), name)
        while not b.done and b.pc != 'publish_cas':
            b.step(q)
        b.step(q)
        self.assertFalse(b.done)             # spins until the earlier claim publishes
        self.assertIsNone(Q.pop_record(q))   # nothing published, so pop returns empty
        a.step(q)
        b.step(q)
        self.assertTrue(a.done and b.done)
        self.assertEqual([Q.pop_record(q), Q.pop_record(q)], [rec(1), rec(2)])

    def test_pop_snapshot_beyond_ring_counts_as_empty(self):
        q = queue()
        struct.pack_into('<I', q, 0x40c, 0x401)
        self.assertIsNone(Q.pop_record(q))

    def test_inflight_reader_keeps_space_reserved(self):
        q = queue()
        for n in range(42):
            Q.push_record(q, rec(n))
        reader = Q.PopOp()
        while reader.pc != 'publish_cas':
            reader.step(q)                   # claimed and copied, not yet published
        with self.assertRaises(Q.RingStalled):
            Q.push_record(q, rec(50), spin_limit=200)
        reader.step(q)
        Q.push_record(q, rec(50))

    def test_custom_base_inside_dispatcher(self):
        d = bytearray(0x728)
        Q.push_record(d, rec(7), base=Q.QUEUE_OFFSET)
        self.assertEqual(struct.unpack_from('<4I', d, 0x618), (0, 0, 24, 24))
        self.assertEqual(Q.pop_record(d, base=Q.QUEUE_OFFSET), rec(7))


class WorkerTests(unittest.TestCase):
    def dispatcher(self):
        d = bytearray(0x728)
        for i in range(4):
            struct.pack_into('<Q', d, 0x118 + 8 * i, 0x500 + i)
        return d

    def test_call_record_counter_order(self):
        d = self.dispatcher()
        struct.pack_into('<I', d, 0x628 + 8, 2)
        struct.pack_into('<I', d, 0x6a8 + 8, 2)
        seen = []
        Q.push_record(d, Q.pack_record(Q.TAG_CALL, 2, 0xcb, 77), base=Q.QUEUE_OFFSET)
        Q.push_record(d, Q.pack_record(Q.TAG_EXIT, 0, 0, 0), base=Q.QUEUE_OFFSET)
        struct.pack_into('<I', d, 0x628, 1)
        struct.pack_into('<I', d, 0x6a8, 1)
        waits = []
        Q.run_job_worker(d, 1, wait=waits.append,
                         invoke=lambda cb, tok, flag: seen.append((cb, tok, flag, (struct.unpack_from('<I', d, 0x628 + 8)[0], struct.unpack_from('<I', d, 0x6a8 + 8)[0]))),
                         fault=lambda *a: self.fail('unexpected fault'))
        self.assertEqual(seen, [(0xcb, 77, False, (1, 2))])
        self.assertEqual(waits, [0x501])     # remaining unclaimed (1) skips the next wait
        self.assertEqual((struct.unpack_from('<I', d, 0x628 + 8)[0], struct.unpack_from('<I', d, 0x6a8 + 8)[0]), (1, 1))
        self.assertEqual((struct.unpack_from('<I', d, 0x628)[0], struct.unpack_from('<I', d, 0x6a8)[0]), (0, 0))

    def test_unknown_tag_only_rereads_counter(self):
        d = self.dispatcher()
        Q.push_record(d, Q.pack_record(0x1234, 3, 1, 2), base=Q.QUEUE_OFFSET)
        self.assertEqual(Q.handle_job_record(d, Q.pop_record(d, base=Q.QUEUE_OFFSET), None), ('ignored', False))
        struct.pack_into('<I', d, 0x628 + 12, 5)
        self.assertEqual(Q.handle_job_record(d, Q.pack_record(0x1234, 3, 1, 2), None), ('ignored', True))
        with self.assertRaises(ValueError):
            Q.handle_job_record(d, Q.pack_record(Q.TAG_CALL, 32, 1, 2), None)

    def test_empty_pop_scans_counters(self):
        d = self.dispatcher()
        waits, faults = [], []

        def wait(h):
            waits.append(h)
            if len(waits) == 2:
                struct.pack_into('<I', d, 0x628 + 4 * 5, 3)
            if len(waits) == 3:
                raise Q.WorkerHalt

        def fault(i, v):
            faults.append((i, v))
            raise Q.WorkerHalt
        with self.assertRaises(Q.WorkerHalt):
            Q.run_job_worker(d, 0, wait=wait, invoke=None, fault=fault)
        self.assertEqual((waits, faults), ([0x500, 0x500], [(5, 3)]))

    def test_exit_records(self):
        d = self.dispatcher()
        struct.pack_into('<I', d, 0xc, 3)
        notified = []
        Q.publish_exit_records(d, notified.append)
        self.assertEqual(notified, [0x501, 0x502])
        self.assertEqual((struct.unpack_from('<I', d, 0x628)[0], struct.unpack_from('<I', d, 0x6a8)[0]), (2, 2))
        for i in (1, 2):
            Q.run_job_worker(d, i, wait=lambda h: None, invoke=None, fault=None)
        self.assertEqual((struct.unpack_from('<I', d, 0x628)[0], struct.unpack_from('<I', d, 0x6a8)[0]), (0, 0))
        self.assertEqual(struct.unpack_from('<4I', d, 0x618), (48, 48, 48, 48))


class DispatcherCompositionTests(unittest.TestCase):
    """engine.pose_dispatch with its enqueue/take services bound to the recovered ring."""

    def setUp(self):
        self.d = bytearray(0x728)
        struct.pack_into('<I', self.d, 0x10, 4)
        for i in range(4):
            struct.pack_into('<Q', self.d, 0x118 + 8 * i, 0x500 + i)
        self.cas, self.add = pose_dispatch_serial_atomics(self.d)
        self.events = []

    def enqueue(self, record):
        Q.push_record(self.d, Q.pack_record(*record), base=Q.QUEUE_OFFSET)

    def take(self):
        raw = Q.pop_record(self.d, base=Q.QUEUE_OFFSET)
        return None if raw is None else Q.unpack_record(raw)

    def invoke(self, fn, arg, caller):
        self.events.append((arg, caller))

    def test_workers_pop_published_records(self):
        def notify(handle):                 # the woken worker consumes one record
            raw = Q.pop_record(self.d, base=Q.QUEUE_OFFSET)
            self.assertIsNotNone(raw)
            self.events.append(('worker', handle - 0x500))
            self.assertEqual(Q.handle_job_record(self.d, raw, lambda f, a, c: self.events.append((a, c)))[0], 'call')
        dispatch_pose_workers(self.d, 3, 7, [10, 11, 12], atomic_compare_exchange=self.cas, atomic_add=self.add,
                              enqueue=self.enqueue, take=self.take, invoke=self.invoke, notify=notify,
                              wait=lambda: self.fail('workers already finished'))
        self.assertEqual(self.events, [('worker', 1), (11, False), ('worker', 2), (12, False), (10, True)])
        self.assertEqual(bytes(self.d[0x628:0x728]), bytes(0x100))
        self.assertEqual(struct.unpack_from('<4I', self.d, 0x618), (48, 48, 48, 48))

    def test_caller_helps_through_ring(self):
        dispatch_pose_workers(self.d, 3, 7, [10, 11, 12], atomic_compare_exchange=self.cas, atomic_add=self.add,
                              enqueue=self.enqueue, take=self.take, invoke=self.invoke, notify=lambda h: None,
                              wait=lambda: self.fail('no wait'))
        self.assertEqual(self.events, [(10, True), (11, True), (12, True)])
        self.assertEqual(bytes(self.d[0x628:0x728]), bytes(0x100))

    def test_helper_can_consume_foreign_record_from_ring(self):
        self.enqueue((Q.TAG_CALL, 3, 8, 99))
        struct.pack_into('<I', self.d, 0x628 + 12, 1)
        struct.pack_into('<I', self.d, 0x6a8 + 12, 1)
        dispatch_pose_workers(self.d, 2, 7, [10, 11], atomic_compare_exchange=self.cas, atomic_add=self.add,
                              enqueue=self.enqueue, take=self.take, invoke=self.invoke, notify=lambda h: None,
                              wait=lambda: self.fail('no wait'))
        # helper takes its own record first (FIFO would give the foreign record first)
        self.assertEqual([e[0] for e in self.events], [10, 99, 11])
        self.assertEqual((struct.unpack_from('<I', self.d, 0x628 + 12)[0], struct.unpack_from('<I', self.d, 0x6a8 + 12)[0]), (0, 0))


class ModelCheckerTests(unittest.TestCase):
    """AUTHORED interleaving exploration of the recovered step machines. Not native evidence."""

    def assertClean(self, report):
        self.assertEqual(report['failures'], {})
        self.assertFalse(report['truncated'])
        self.assertTrue(report['initial_can_finish'])

    def test_two_producers_one_consumer_wrapping_two_slot_ring(self):
        r = explore([('push', [rec(1), rec(3)]), ('push', [rec(2), rec(4)]), ('pop', 3)], ring=0x40)
        self.assertClean(r)
        self.assertEqual((r['states'], r['terminal_states']), (19541, 24))

    def test_two_producers_two_consumers_across_counter_wrap(self):
        r = explore([('push', [rec(1), rec(3)]), ('push', [rec(2), rec(4)]), ('pop', 2), ('pop', 2)],
                    ring=0x40, start=0xffffffc8, max_states=1000000)
        self.assertClean(r)
        self.assertEqual(r['states'], 447557)

    def test_larger_ring(self):
        self.assertClean(explore([('push', [rec(1), rec(3)]), ('push', [rec(2), rec(4)]), ('pop', 2)], ring=0x80))

    def test_full_ring_producer_waits_for_consumer(self):
        self.assertClean(explore([('push', [rec(1)]), ('pop', 2), ('pop', 2)], ring=0x40, preload=2))

    def test_full_ring_without_consumer_never_finishes(self):
        r = explore([('push', [rec(1)])], ring=0x40, preload=2)
        self.assertEqual((r['terminal_states'], r['initial_can_finish'], r['failures']), (0, False, {}))

    def test_empty_ring_pop_returns_empty(self):
        r = explore([('pop', 3)], ring=0x40)
        self.assertClean(r)
        self.assertEqual(r['terminal_states'], 1)

    def test_checker_detects_unordered_publication(self):
        original = Q.PushOp.step

        def bad(self, buf):
            if self.pc == 'publish_cas':        # mutant: publish without waiting for the earlier writer
                import struct as s
                s.pack_into('<I', buf, self.ring + 0xc, (self.b + 24) & 0xffffffff)
                self.pc, self.done = 'done', True
                return 'publish_cas'
            return original(self, buf)
        Q.PushOp.step = bad
        try:
            r = explore([('push', [rec(1)]), ('push', [rec(2)]), ('pop', 2)], ring=0x40, max_states=5000)
        finally:
            Q.PushOp.step = original
        self.assertTrue(r['failures'])

    def test_checker_detects_missing_space_check(self):
        original = Q.PushOp.step

        def bad(self, buf):
            r = original(self, buf)
            if r == 'load_write_claim' and self.pc == 'load_read_published':
                self.pc = 'claim_cas'               # mutant: ignore a full ring
            return r
        Q.PushOp.step = bad
        try:
            r = explore([('push', [rec(1)]), ('pop', 1)], ring=0x40, preload=2, max_states=5000)
        finally:
            Q.PushOp.step = original
        self.assertTrue(r['failures'])


if __name__ == '__main__':
    unittest.main()
