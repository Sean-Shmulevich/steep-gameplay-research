import unittest
from engine.action_cache_policy import choose_input_cache


class CachePolicyTests(unittest.TestCase):
    def decide(self, **changes):
        args = dict(scan_begin=0, scan_end=3, fallback_flag=1, record_count=4,
                    record_ids=(8, 9, 10), query=lambda value: 1)
        args.update(changes)
        return choose_input_cache(**args)

    def test_first_zero_short_circuits(self):
        seen = []
        def query(value):
            seen.append(value)
            return 0 if value == 9 else 1
        self.assertEqual(self.decide(query=query), dict(selected_index=1,
                         queried_indices=(0, 1), final_notifications=False))
        self.assertEqual(seen, [8, 9])

    def test_zero_outside_count_does_not_fall_back(self):
        result = self.decide(record_count=1, fallback_flag=0,
                             query=lambda value: int(value != 9))
        self.assertIsNone(result['selected_index'])
        self.assertFalse(result['final_notifications'])

    def test_unsigned_flag_and_scan_end_fallback(self):
        self.assertEqual(self.decide(fallback_flag=0xffffffff)['selected_index'], 3)
        self.assertIsNone(self.decide(record_count=3)['selected_index'])

    def test_empty_zero_fallback_still_notifies(self):
        result = self.decide(scan_begin=7, scan_end=3, record_count=0, fallback_flag=0)
        self.assertEqual(result, dict(selected_index=None, queried_indices=(),
                                     final_notifications=True))
        self.assertEqual(self.decide(fallback_flag=0)['selected_index'], 0)

    def test_missing_record_and_invalid_query(self):
        with self.assertRaises(ValueError):
            self.decide(record_ids=())
        with self.assertRaises(ValueError):
            self.decide(query=lambda value: -1)
        with self.assertRaises(ValueError):
            self.decide(scan_begin=-1)
