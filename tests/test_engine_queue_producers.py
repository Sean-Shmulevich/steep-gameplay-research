import unittest
from engine.queue_producers import worker_configuration, worker_mask, enqueue_destination, base_job_limit, range_configuration, range_should_yield
from engine.queue_policy import select_queue


class QueueProducerTests(unittest.TestCase):
    def test_unsigned_clamp_and_signed_storage(self):
        self.assertEqual(worker_configuration(0, 8), dict(worker_count=1, shared_default=1, auxiliary_count=1))
        self.assertEqual(worker_configuration(8, 3)['worker_count'], 3)
        self.assertEqual(worker_configuration(8, 0), dict(worker_count=0, shared_default=0, auxiliary_count=1))
        self.assertEqual(worker_configuration(0xffffffff, 0xffffffff),
                         dict(worker_count=0xffffffff, shared_default=-1, auxiliary_count=1))
        self.assertEqual(worker_configuration(0x80000000, 0xffffffff)['auxiliary_count'], 0x7fffffff)

    def test_mask_rotation_wraps_without_allocating(self):
        self.assertEqual([worker_mask(i) for i in (0, 31, 32, 33)], [1, 0x80000000, 1, 2])

    def test_lowest_required_bit_owns_route(self):
        self.assertEqual(enqueue_destination(2, 6, [True]*3),
                         dict(category=2, queue='local', worker_index=1))
        self.assertEqual(enqueue_destination(2, 6, [True, False, True]),
                         dict(category=2, queue='shared', worker_index=None))
        self.assertEqual(enqueue_destination(0, 0, [])['queue'], 'shared')

    def test_missing_slot_is_not_null_slot(self):
        with self.assertRaises(ValueError):
            enqueue_destination(0, 4, [True])
        self.assertEqual(enqueue_destination(0, 4, [True, True, False])['queue'], 'shared')

    def test_routing_then_local_selection_bypasses_exclusion(self):
        route = enqueue_destination(0, 2, [True, True])
        jobs = {'job': dict(kind='callback', limit=1, executions=0,
                            required_mask=2, excluded_mask=2)}
        self.assertEqual(select_queue(jobs, ['job'], shared_default=2,
                         worker_mask=worker_mask(route['worker_index']),
                         local=route['queue']=='local')['selected'], 'job')
        self.assertIsNone(select_queue(jobs, ['job'], shared_default=2,
                          worker_mask=2, local=False)['selected'])

    def test_invalid_inputs_remain_explicit(self):
        for value in (-1, 2**32, True, 1.5):
            with self.assertRaises(ValueError): worker_configuration(value, 8)
            with self.assertRaises(ValueError): worker_mask(value)
        with self.assertRaises(ValueError): enqueue_destination(3, 0, [])
        with self.assertRaises(ValueError): enqueue_destination(0, 1, [1])

    def test_base_limit_signed_comparison_then_byte_conversion(self):
        for argument, default, expected in ((255, 8, 8), (8, 255, 8),
                (255, 256, 255), (255, 0, 0), (0, -1, 255),
                (255, -256, 0), (1, -257, 255), (255, -2147483648, 0)):
            with self.subTest(argument=argument, default=default):
                self.assertEqual(base_job_limit(argument, default), expected)
        for argument in (-1, 256, True):
            with self.assertRaises(ValueError): base_job_limit(argument, 8)

    def test_range_configuration_signed_boundaries(self):
        self.assertEqual(range_configuration(-1), dict(chunk_size=1, tail_threshold=2))
        self.assertEqual(range_configuration(32), dict(chunk_size=32, tail_threshold=64))
        self.assertEqual(range_configuration(2**30)['tail_threshold'], -2**31)
        self.assertEqual(range_configuration(2**31-1)['tail_threshold'], 0)
        with self.assertRaises(ValueError): range_configuration(True)

    def test_configured_before_physics_claims_preserve_tail_and_completion(self):
        from engine.mixed_scheduler import MixedScheduler
        scheduler = MixedScheduler([dict(id='before', kind='range',
            receivers=list(range(100)), **range_configuration(32))])
        scheduler.submit('before')
        token = scheduler.reserve()
        claims = []
        while (claim := scheduler.claim_range(token)) is not None:
            claims.append((claim.start, claim.count))
            scheduler.execute_range(token, claim)
        self.assertEqual(claims[:2], [(68, 32), (64, 4)])
        self.assertEqual(claims[2:], [(i, 1) for i in range(63, -1, -1)])
        self.assertEqual(scheduler.snapshot()['jobs']['before']['executions'], 1)
        scheduler.finish_dispatch(token)
        self.assertEqual(scheduler.snapshot()['jobs']['before']['executions'], 0)

    def test_post_range_yield_signals_are_distinct(self):
        self.assertFalse(range_should_yield(7,7,False,1))
        self.assertFalse(range_should_yield(7,7,True,0))
        self.assertTrue(range_should_yield(7,8,False,0))
        self.assertTrue(range_should_yield(7,7,True,1))
        self.assertTrue(range_should_yield(7,7,True,-1))
        self.assertTrue(range_should_yield(0xffffffff,0,False,0))
        with self.assertRaises(ValueError):range_should_yield(0,0,1,0)
