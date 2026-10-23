import unittest
from engine.publication_input_join import compare_publications


def row(start, end, bits=(0, 0, 0, 0), valid=True):
    return dict(entry=start, exit=end, bits=bits, valid=valid)


class PublicationInputJoinTests(unittest.TestCase):
    def test_sign_bit_preserves_negative_zero_and_nan_payload(self):
        bits = (0, 0x7fc12345, 0x80000000, 0)
        sources = [row(0, 1, bits), row(10, 11)]
        target = row(2, 3, (0x80000000, *bits[1:]))
        self.assertEqual(compare_publications(sources, [target], flip_x=True)['counts'], {'match': 1})
        self.assertEqual(compare_publications(sources, [target], flip_x=False)['counts'], {'mismatch': 1})

    def test_invalid_latest_never_falls_back(self):
        sources = [row(0, 1), row(3, 4, valid=False), row(10, 11)]
        self.assertEqual(compare_publications(sources, [row(5, 6)], flip_x=False)['counts'], {'invalid_latest_parent': 1})

    def test_boundaries_and_missing_coverage(self):
        sources = [row(2, 3), row(10, 11)]
        targets = [row(0, 1), row(3, 10), row(9, 12), row(12, 13), row(4, 5, valid=False)]
        result = compare_publications(sources, targets, flip_x=False)
        self.assertEqual(result['counts'], {'no_completed_parent': 1, 'match': 1,
            'overlapping_next_parent': 1, 'unbounded_tail': 1, 'invalid_target': 1})

    def test_ambiguous_and_invalid_inputs_refused(self):
        for sources in ([row(0, 4), row(2, 3)], [row(0, 0), row(0, 1)]):
            with self.assertRaises(ValueError):compare_publications(sources, [], flip_x=False)
        with self.assertRaises(ValueError):compare_publications([], [], flip_x=None)
        with self.assertRaises(ValueError):compare_publications([row(1, 0)], [], flip_x=False)


class DeliveryCoverageTests(unittest.TestCase):
    def test_delayed_input_is_not_covered(self):
        from engine.publication_input_join import delivery_window_coverage as check
        self.assertFalse(check([(10, 20), (30, 40)], key_down=41, key_up=45)['covered'])
        self.assertFalse(check([(10, 20), (30, 40)], key_down=25, key_up=28)['covered'])
        self.assertFalse(check([(10, 20)], key_down=15, key_up=25)['covered'])
        self.assertTrue(check([(10, 20), (30, 40)], key_down=15, key_up=35)['covered'])
        self.assertFalse(check([], key_down=1, key_up=2)['covered'])
        with self.assertRaises(ValueError):check([(20, 10)], key_down=1, key_up=2)
