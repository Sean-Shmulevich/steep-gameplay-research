import unittest
from engine.allocation_context_resolver import resolve_allocation_context


class AllocationContextResolverTests(unittest.TestCase):
    def resolve(self, size, alignment, query=lambda token: 16, **kw):
        return resolve_allocation_context(size, alignment, 999,
            small_contexts=list(range(100, 115)),
            special_contexts={80: 200, 96: 201, 128: 202},
            query_alignment=query, **kw)

    def test_auto_alignment_and_minimum_class(self):
        self.assertEqual(self.resolve(0, 0xffffffff), 102)
        self.assertEqual(self.resolve(1, 0xffffffff), 100)
        self.assertEqual(self.resolve(9, 0xffffffff), 101)
        self.assertEqual(self.resolve(16, 0xffffffff), 102)
        self.assertEqual(self.resolve(64, 0xffffffff), 114)

    def test_exact_special_sizes_and_query_boundary(self):
        calls = []
        def query(token):
            calls.append(token); return 16
        self.assertEqual(self.resolve(80, 16, query), 200)
        self.assertEqual(self.resolve(96, 17, query), 0)
        self.assertEqual(self.resolve(128, 16, query), 202)
        self.assertEqual(self.resolve(81, 16, query), 0)
        self.assertEqual(calls, [200, 201, 202])

    def test_no_query_for_small_table_or_unsupported_sizes(self):
        def forbidden(token):
            self.fail('unexpected virtual query')
        self.assertEqual(self.resolve(64, 8, forbidden), 114)
        self.assertEqual(self.resolve(65, 8, forbidden), 0)
        self.assertEqual(self.resolve(384, 8, forbidden), 0)

    def test_non_power_of_two_and_wrap_are_not_normalized(self):
        self.assertEqual(self.resolve(9, 6), 100)
        self.assertEqual(self.resolve(1, 0xfffffffe), 100)
