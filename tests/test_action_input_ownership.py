import unittest
from engine.action_input_ownership import priority_blocks, cache_owner_blocks


class OwnershipTests(unittest.TestCase):
    def test_first_nonzero_wins(self):
        for index in range(7):
            for owner, blocked in ((42, False), (99, True)):
                slots = [0]*index + [owner] + [123]*(6-index)
                self.assertEqual(priority_blocks(slots, 42), blocked)
        self.assertFalse(priority_blocks([0]*7, 42))

    def test_priority_and_cache_ownership_differ(self):
        self.assertFalse(priority_blocks([42]+[0]*6, 42))
        self.assertTrue(cache_owner_blocks([42]))
        self.assertFalse(cache_owner_blocks([42, 0]))
        self.assertFalse(cache_owner_blocks([]))

    def test_bounds(self):
        with self.assertRaises(ValueError): priority_blocks([0]*6, 42)
        with self.assertRaises(ValueError): cache_owner_blocks([-1])
