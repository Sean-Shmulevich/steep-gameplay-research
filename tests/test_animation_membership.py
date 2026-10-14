import unittest
from engine.animation_membership import AnimationMembership
from engine.animation_batch import visit_animation_batch


class AnimationMembershipTests(unittest.TestCase):
    def test_empty_preserves_active_count_and_storage(self):
        state = AnimationMembership(['prior', 'unused'], 1)
        storage = state.storage
        self.assertFalse(state.copy_registry([]))
        self.assertIs(state.storage, storage)
        self.assertEqual(state.count, 1)
        self.assertEqual(state.storage, ['prior', 'unused'])

    def test_reuse_preserves_tail_and_copies_object_references(self):
        first, second = object(), object()
        source = [first, second]
        state = AnimationMembership([None, None, 'tail'], 3)
        storage = state.storage
        self.assertFalse(state.copy_registry(source))
        source[0] = None
        self.assertIs(state.storage, storage)
        self.assertIs(state.storage[0], first)
        self.assertIs(state.storage[1], second)
        self.assertEqual(state.storage[2], 'tail')
        self.assertEqual(state.count, 2)

    def test_growth_then_batch_visitation(self):
        state = AnimationMembership(['old'], 1)
        storage = state.storage
        self.assertTrue(state.copy_registry(['first', 'second', 'third']))
        self.assertIsNot(state.storage, storage)
        self.assertEqual(state.count, 3)
        seen = []
        visit_animation_batch({'callback': seen.append}, state.storage, state.count)
        self.assertEqual(seen, ['third', 'second', 'first'])

    def test_invalid_destination_count(self):
        for count in (-1, True, 2):
            with self.assertRaises(ValueError):
                AnimationMembership([None], count).copy_registry([])

    def test_claim_reaches_zero_before_any_callback(self):
        state = AnimationMembership(['first', 'second'], 2)
        span = state.claim(2, 0)
        self.assertEqual(state.count, 0)
        self.assertEqual(list(span), ['first', 'second'])
        self.assertIsNone(state.claim())
        seen = []
        visit_animation_batch({'callback': seen.append}, span)
        self.assertEqual(seen, ['second', 'first'])

    def test_claimed_span_reads_entries_late(self):
        state = AnimationMembership(['first', 'second', 'third'], 3)
        span = state.claim(2, 0)
        self.assertEqual((span.start, span.count, state.count), (1, 2, 1))
        state.storage[1] = 'changed'
        self.assertEqual(list(span), ['changed', 'third'])
        self.assertEqual(span[-1], 'third')
        self.assertEqual(span[:1], ['changed'])
        with self.assertRaises(IndexError):
            _ = span[2]

    def test_complete_and_partial_claim_then_empty_gather(self):
        state = AnimationMembership(list(range(5)), 5)
        first = state.claim(2, 0)
        state.copy_registry([])
        self.assertEqual(state.count, 3)
        ranges = [first]
        while (span := state.claim(2, 0)) is not None:
            ranges.append(span)
        state.copy_registry([])
        self.assertEqual(state.count, 0)
        self.assertEqual(state.storage, list(range(5)))
        self.assertEqual([(s.start, s.count) for s in ranges], [(3, 2), (1, 2), (0, 1)])

    def test_invalid_claim_does_not_change_count(self):
        state = AnimationMembership([1, 2], 2)
        for chunk, tail in [(0, 0), (1, -1), (True, 0)]:
            with self.assertRaises(ValueError):
                state.claim(chunk, tail)
            self.assertEqual(state.count, 2)
