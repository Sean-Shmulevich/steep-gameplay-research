import unittest
from engine.command_drain import command_quota, drain_primary


class CommandDrainTests(unittest.TestCase):
    def drain(self, count, quota, elapsed=0, bypass=False, inject=False):
        queue = list(range(count))
        clock = iter([0] + [elapsed] * (count + 2))
        processed = []
        def take():
            return (True, queue.pop(0)) if queue else (False, None)
        def process(record):
            processed.append(record)
            if inject:
                queue.append(record)
        result = drain_primary(quota=quota, bypass_budget=bypass, take=take,
                               process=process, ticks=lambda: next(clock),
                               frequency=1000000, max_attempts=8)
        return result, queue, processed

    def test_quota_threshold_and_override(self):
        self.assertEqual(command_quota(6, 8), 1)
        self.assertEqual(command_quota(7, 8), 3)
        self.assertEqual(command_quota(7, 9), 3)
        self.assertEqual(command_quota(0, 8, snapshot_override=True), 0)
        self.assertEqual(command_quota(6, 8, snapshot_override=True), 6)

    def test_time_boundary_is_strict_and_after_command(self):
        self.assertEqual(self.drain(3, 3, 10000)[0]['processed'], 3)
        result, queue, seen = self.drain(3, 3, 10001)
        self.assertEqual((seen, queue, result['elapsed_us']), ([0], [1, 2], 10001))

    def test_bypass_ignores_count_and_clock_budget(self):
        result, queue, seen = self.drain(3, 1, 999999, True)
        self.assertEqual((result['attempts'], result['processed'], queue), (4, 3, []))
        self.assertIsNone(result['elapsed_us'])

    def test_zero_quota_still_attempts_then_wraps(self):
        result, queue, seen = self.drain(2, 0)
        self.assertEqual((result['attempts'], seen), (3, [0, 1]))
        self.assertEqual(result['remaining_quota'], 0xfffffffd)
        self.assertFalse(self.drain(0, 0)[0]['did_work'])

    def test_clock_wrap_and_product_wrap(self):
        for start, end, expected in [(2**64-2, 1, 3), (0, 2**63, 0)]:
            clock = iter([start, end])
            result = drain_primary(quota=1, bypass_budget=False, take=lambda:(True, 'x'),
                                   process=lambda x:None, ticks=lambda:next(clock), frequency=1000000)
            self.assertEqual(result['elapsed_us'], expected)

    def test_authored_limit_bounds_continually_refilled_queue(self):
        with self.assertRaisesRegex(RuntimeError, 'authored'):
            self.drain(1, 1, bypass=True, inject=True)


if __name__ == '__main__':
    unittest.main()
