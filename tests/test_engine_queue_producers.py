import unittest
from engine.queue_producers import worker_configuration, worker_mask, enqueue_destination, base_job_limit
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
