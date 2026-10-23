import unittest
from engine.allocation_policy import allocate_bytes, select_allocation_context


class AllocationPolicyTests(unittest.TestCase):
    def select(self, size, source, resolve=lambda *args: 0):
        return select_allocation_context(size, 8, source, special_a=11, special_b=22,
                                         coarse_source=33, override_source=44, resolve=resolve)

    def test_special_source_skips_resolver_and_comparison_is_strict(self):
        def forbidden(*args):
            self.fail('special source must skip resolver')
        self.assertEqual(self.select(61681, 11, forbidden), 11)
        self.assertEqual(self.select(61682, 11, forbidden), 44)
        self.assertEqual(self.select(64528, 33), 33)
        self.assertEqual(self.select(64529, 33), 44)

    def test_resolved_nonzero_wins_over_fallback_arithmetic(self):
        self.assertEqual(self.select(65536, 55, lambda *args: 99), 99)
        self.assertEqual(self.select(65536, 55), 44)

    def test_zero_size_invokes_no_allocator_services(self):
        def forbidden(*args):
            self.fail('zero-sized request must not dispatch')
        self.assertEqual(allocate_bytes(0, 17, 0, current_allocator=forbidden,
                         allocate_default=forbidden, allocate_aligned=forbidden, recover=forbidden), 0)

    def test_retry_reloads_allocator_and_never_recovers_twice(self):
        events = []
        identity = [1]
        def allocate(allocator, size, context):
            events.append(('allocate', allocator, size, context))
            return 0
        def recover(*args):
            events.append(('recover', args)); identity[0] = 2
            return 257
        result = allocate_bytes(384, 16, 77, current_allocator=lambda: identity[0],
                    allocate_default=allocate, allocate_aligned=lambda *args: self.fail('wrong dispatch'),
                    recover=recover)
        self.assertEqual(result, 0)
        self.assertEqual(events, [('allocate', 1, 384, 77), ('recover', (1, 384, 0, 0, 0)),
                                  ('allocate', 2, 384, 77)])

    def test_recovery_low_byte_zero_prevents_retry(self):
        calls = []
        def allocate(*args):
            calls.append(args); return 0
        self.assertEqual(allocate_bytes(384, 8, 77, current_allocator=lambda: 1,
                         allocate_default=allocate, allocate_aligned=allocate, recover=lambda *args: 256), 0)
        self.assertEqual(len(calls), 1)

    def test_alignment_17_selects_aligned_method(self):
        calls = []
        def aligned(*args):
            calls.append(args); return 123
        result = allocate_bytes(384, 17, 77, current_allocator=lambda: 1,
                    allocate_default=lambda *args: self.fail('wrong dispatch'), allocate_aligned=aligned,
                    recover=lambda *args: self.fail('successful request must not recover'))
        self.assertEqual(result, 123)
        self.assertEqual(calls, [(1, 384, 17, 77)])

    def test_unsigned_input_contract(self):
        with self.assertRaises(ValueError):
            self.select(-1, 11)
        with self.assertRaises(ValueError):
            self.select(2**32, 11)
