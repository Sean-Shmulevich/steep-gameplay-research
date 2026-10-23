import unittest
from engine.action_cache_counts import count_inserted_cache


class CacheCountsTests(unittest.TestCase):
    def run_kind(self, kind, **changes):
        args = dict(kind=kind, scan_begin=0, scan_end=0, fallback_count=0,
                    kind9_count=0, record_id=65535)
        args.update(changes)
        return count_inserted_cache(**args)

    def test_category_boundaries(self):
        self.assertEqual(self.run_kind(0), dict(scan_begin=1, scan_end=1,
                         fallback_count=0, kind9_count=0, query_id=0xffffffff))
        for kind in (2, 6, 7, 8, 10):
            self.assertEqual(self.run_kind(kind), dict(scan_begin=0, scan_end=1,
                             fallback_count=0, kind9_count=0, query_id=65535))
        for kind in (1, 3, 4, 5, 11, 32, 0xffffffff):
            self.assertEqual(self.run_kind(kind)['fallback_count'], 1)
        self.assertEqual(self.run_kind(9)['kind9_count'], 1)

    def test_wrap_and_untouched_counters(self):
        result = self.run_kind(9, fallback_count=0xffffffff, kind9_count=0xffffffff,
                               scan_begin=5, scan_end=7)
        self.assertEqual(result, dict(scan_begin=5, scan_end=7, fallback_count=0,
                                     kind9_count=0, query_id=0xffffffff))

    def test_four_initial_records(self):
        state = dict(scan_begin=0, scan_end=0, fallback_count=0, kind9_count=0)
        for ident in range(4):
            result = count_inserted_cache(kind=8, record_id=ident, **state)
            self.assertEqual(result.pop('query_id'), ident)
            state = result
        self.assertEqual(state, dict(scan_begin=0, scan_end=4, fallback_count=0,
                                    kind9_count=0))

    def test_invalid_id(self):
        with self.assertRaises(ValueError):
            self.run_kind(8, record_id=65536)
