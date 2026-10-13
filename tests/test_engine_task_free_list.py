import unittest

from engine.tagged_task_queue import free_pop_decision, free_push_decision


class TaskFreeListTests(unittest.TestCase):
    def test_return_then_allocate_preserves_chain(self):
        push = free_push_decision((3 << 48) | 20, 10)
        self.assertEqual(push['before_cas'], dict(node=10, next=20))
        pop = free_pop_decision(push['desired'], node_next=20)
        self.assertEqual(pop['on_success']['return_node'], 10)
        self.assertEqual(pop['desired'], (5 << 48) | 20)

    def test_same_pointer_after_reuse_has_different_expected_tag(self):
        original = (7 << 48) | 10
        stale = free_pop_decision(original, node_next=20)
        # Another owner pops then returns node 10. The pointer is unchanged,
        # but the original expected word cannot pass a full-word CAS.
        current = free_push_decision(stale['desired'], 10)['desired']
        self.assertEqual(current & ((1 << 48) - 1), 10)
        self.assertNotEqual(current, stale['expected'])
        self.assertEqual(free_pop_decision(current, node_next=20)['on_failure'], 'reload')

    def test_finite_tag_wrap_is_not_a_permanent_identity(self):
        initial = 10
        current = initial
        for _ in range(32768):
            current = free_pop_decision(current, node_next=0)['desired']
            current = free_push_decision(current, 10)['desired']
        self.assertEqual(current, initial)
        # Arithmetic counterexample to permanent uniqueness, not evidence that
        # a native stale reader survives this many legal reuse operations.

    def test_empty_uses_pointer_bits_and_nonempty_requires_link(self):
        self.assertEqual(free_pop_decision(99 << 48), dict(action='empty'))
        for bad in (None, True, -1, 1 << 64):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                free_pop_decision(10, node_next=bad)
        for bad in (0, True, 1 << 48):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                free_push_decision(0, bad)
