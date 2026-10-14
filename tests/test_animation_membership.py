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
