import unittest
from engine.kino_event_routes import kino_event_slots, kino_removal_slots
from engine.event_registry import WorldEventRegistry


class KinoEventRouteTests(unittest.TestCase):
    def test_mode_low_bits_only(self):
        for high in range(32):
            for low in range(8):
                self.assertEqual(kino_event_slots(high * 8 + low), (16, 23 if low == 1 else 22))

    def test_component_token_and_cleanup_after_mode_change(self):
        registry = WorldEventRegistry()
        component, owning_context = 100, 200
        for slot in kino_event_slots(1):
            registry.register(slot, component)
        self.assertEqual(registry.snapshot(16), [component])
        self.assertEqual(registry.snapshot(23), [component])
        self.assertNotIn(owning_context, registry.snapshot(16))
        # Cleanup must not choose only slot 22 from a newly changed mode.
        self.assertEqual(kino_event_slots(2), (16, 22))
        for slot in kino_removal_slots():
            registry.remove(slot, component)
        self.assertEqual([registry.snapshot(s) for s in (16, 22, 23)], [[], [], []])

    def test_invalid_mode(self):
        for mode in (-1, 256, True, 1.0):
            with self.assertRaises(ValueError):
                kino_event_slots(mode)
