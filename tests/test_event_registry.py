import unittest
from engine.event_registry import WorldEventRegistry, event_source_offset, remove_listener
from engine.animation_membership import AnimationMembership
from engine.animation_batch import visit_animation_batch


class EventRegistryTests(unittest.TestCase):
    def test_identity_uniqueness_and_slot_isolation(self):
        registry = WorldEventRegistry()
        self.assertTrue(registry.register(16, 100))
        self.assertFalse(registry.register(16, 100))
        self.assertTrue(registry.register(17, 100))
        registry.register(16, 101)
        self.assertEqual(registry.snapshot(16), [100, 101])
        self.assertEqual(registry.snapshot(17), [100])
        copy = registry.snapshot(16)
        copy.clear()
        self.assertEqual(registry.snapshot(16), [100, 101])

    def test_removal_reorders_next_animation_batch(self):
        registry = WorldEventRegistry()
        for token in (10, 20, 30, 40):
            registry.register(16, token)
        prior = AnimationMembership()
        prior.copy_registry(registry.snapshot(16))
        self.assertTrue(registry.remove(16, 20))
        self.assertEqual(registry.snapshot(16), [10, 40, 30])
        self.assertEqual(prior.storage, [10, 20, 30, 40])
        next_batch = AnimationMembership()
        next_batch.copy_registry(registry.snapshot(16))
        seen = []
        visit_animation_batch({'callback': seen.append}, next_batch.claim(3))
        self.assertEqual(seen, [30, 40, 10])

    def test_first_duplicate_missing_last_and_empty_removal(self):
        entries = [1, 2, 1, 3]
        self.assertTrue(remove_listener(entries, 1))
        self.assertEqual(entries, [3, 2, 1])
        self.assertFalse(remove_listener(entries, 9))
        self.assertTrue(remove_listener(entries, 1))
        self.assertEqual(entries, [3, 2])
        self.assertFalse(remove_listener([], 1))

    def test_slot_mapping_and_adapter_bounds(self):
        self.assertEqual(event_source_offset(16), 0x530)
        self.assertEqual(event_source_offset(24), 0x730)
        registry = WorldEventRegistry()
        for bad in (-1, 53, True):
            with self.assertRaises(ValueError):
                registry.snapshot(bad)
        for bad in (-1, True, 1 << 64):
            with self.assertRaises(ValueError):
                registry.register(16, bad)
