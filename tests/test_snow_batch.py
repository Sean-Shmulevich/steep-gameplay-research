import unittest
from engine.snow_batch import gather_snow_records, requested_claim_size


class SnowBatchTests(unittest.TestCase):
    def test_gather_preserves_duplicates_and_tag_order(self):
        records = gather_snow_records(['a', 'b', 'a'], ['a', 'c'])
        self.assertEqual([(r.tag, r.actor) for r in records],
                         [(0, 'a'), (0, 'b'), (0, 'a'), (2, 'a'), (2, 'c')])

    def test_snapshot_is_detached_and_empty_is_empty(self):
        source = ['a']; result = gather_snow_records(source, [])
        source[0] = 'b'
        self.assertEqual(result[0].actor, 'a')
        self.assertEqual(gather_snow_records([], []), ())

    def test_alternate_records_participate_in_partition(self):
        records = gather_snow_records(['a'], ['other'] * 39)
        self.assertEqual(requested_claim_size(len(records)), 2)

    def test_boundaries(self):
        for n, expected in [(0,1), (19,1), (20,1), (39,1), (40,2), (59,2), (60,3), (65535,3276)]:
            self.assertEqual(requested_claim_size(n), expected)
        for n in [-1, 65536, True, 1.0]:
            with self.assertRaises(ValueError): requested_claim_size(n)
        with self.assertRaises(ValueError): gather_snow_records([0] * 16384, [])
        with self.assertRaises(ValueError): gather_snow_records([object()], [])
        with self.assertRaises(ValueError): gather_snow_records(iter([1]), [])
