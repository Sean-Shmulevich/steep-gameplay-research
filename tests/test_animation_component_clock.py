import unittest
from engine.animation_component_clock import component_interval, dispatch_component_update


class AnimationComponentClockTests(unittest.TestCase):
    def interval(self, **changes):
        args = dict(component_flags=0, owner_present=True, world_present=True,
                    owner_flags=0, ordinary_interval=.125, alternate_interval=.5)
        args.update(changes)
        return component_interval(**args)

    def test_owner_clock_selection(self):
        self.assertEqual(self.interval(), .125)
        self.assertEqual(self.interval(owner_flags=1 << 58), .5)
        self.assertEqual(self.interval(owner_flags=(1 << 58) - 1), .125)
        self.assertEqual(self.interval(component_flags=253), .125)

    def test_forced_zero_does_not_read_clock(self):
        for changes in (dict(component_flags=2), dict(owner_present=False), dict(world_present=False)):
            self.assertEqual(self.interval(ordinary_interval=None, alternate_interval=None, **changes), 0)

    def test_copy_rounding_and_validation(self):
        self.assertEqual(self.interval(ordinary_interval=16777217), 16777216)
        self.assertEqual(self.interval(ordinary_interval=-.25), -.25)
        for changes in (dict(owner_flags=-1), dict(component_flags=256), dict(world_present=1),
                        dict(ordinary_interval=float('inf'))):
            with self.assertRaises(ValueError):self.interval(**changes)

    def test_dispatch_requires_three_local_gates(self):
        for bits in range(8):
            self.assertEqual(dispatch_component_update(interface_ready=bool(bits&1),
                auxiliary_present=bool(bits&2), auxiliary_ready=bool(bits&4)), bits==7)
