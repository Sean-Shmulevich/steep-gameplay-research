import unittest
from engine.world_clock import clock_interval


class WorldClockTests(unittest.TestCase):
    def run_clock(self, **kw):
        return clock_interval(**(dict(input_ms=1000, previous_interval=.25) | kw))

    def test_units_and_history(self):
        r = self.run_clock()
        self.assertEqual((r['interval'], r['ticks'], r['reciprocal'], r['previous_interval']), (1, 30000, 1, .25))

    def test_hold_applies_pending_before_interval(self):
        self.assertEqual(self.run_clock(hold_count=1)['interval'], 0)
        r = self.run_clock(hold_count=1, pending_holds=-1)
        self.assertEqual((r['hold_count'], r['previous_hold_count'], r['pending_holds'], r['interval']), (0, 1, 0, 1))
        self.assertEqual(self.run_clock(hold_count=2147483647, pending_holds=1)['hold_count'], -2147483648)

    def test_minimum_only_with_both_scales(self):
        for primary, secondary, expected_positive in [(False, False, False), (True, False, False), (False, True, False), (True, True, True)]:
            r = self.run_clock(input_ms=0, scale_enabled=primary, secondary_enabled=secondary)
            self.assertEqual(r['interval'] > 0, expected_positive)
        self.assertEqual(self.run_clock(input_ms=-1000, secondary_enabled=True)['interval'], -1)

    def test_reciprocal_deadband_and_scale_order(self):
        self.assertEqual(self.run_clock(input_ms=.001)['reciprocal'], 0)
        self.assertNotEqual(self.run_clock(input_ms=.02)['reciprocal'], 0)
        self.assertEqual(self.run_clock(scale_enabled=True, secondary_enabled=True, scale=.5, secondary_scale=.25)['interval'], .125)

    def test_adapter_rejections(self):
        for kw in [dict(input_ms=float('nan')), dict(input_ms=True), dict(scale_enabled=1), dict(hold_count=True), dict(input_ms=1e30)]:
            with self.assertRaises(ValueError): self.run_clock(**kw)
