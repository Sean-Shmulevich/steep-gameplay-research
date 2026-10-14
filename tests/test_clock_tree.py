import unittest
from engine.clock_tree import ClockState, advance_clock, request_hold


class ClockTreeTests(unittest.TestCase):
    def test_nested_holds_are_deferred_and_balanced(self):
        s=ClockState(interval=.25)
        s=request_hold(request_hold(s))
        self.assertEqual((s.hold_count,s.pending_holds,s.interval),(0,2,.25))
        s=advance_clock(s,100)
        self.assertEqual((s.hold_count,s.pending_holds,s.interval,s.counter),(2,0,0,1))
        s=advance_clock(request_hold(s,release=True),100)
        self.assertEqual(s.interval,0)
        s=advance_clock(request_hold(s,release=True),100)
        self.assertGreater(s.interval,0)

    def test_parent_previous_child_can_advance_while_parent_held(self):
        s=ClockState(interval=.25,pending_holds=1,children=(ClockState(),ClockState(use_parent_previous=True)))
        r=advance_clock(s,100)
        self.assertEqual([r.interval,*[c.interval for c in r.children]],[0,0,.25])
        r=advance_clock(r,100)
        self.assertEqual(r.children[1].interval,0)

    def test_no_accumulation_still_updates_time_and_children(self):
        s=ClockState(counter=4,accumulated_ticks=100,divided_ticks=3,children=(ClockState(),))
        r=advance_clock(s,250,accumulate=False)
        self.assertEqual((r.counter,r.accumulated_ticks,r.divided_ticks,r.toggle),(4,100,3,1))
        self.assertEqual(r.children[0].interval,.25)

    def test_wrap_and_negative_pending(self):
        s=ClockState(pending_holds=2147483647)
        self.assertEqual(request_hold(s).pending_holds,-2147483648)
        r=advance_clock(ClockState(counter=0xffffffff,accumulated_ticks=(1<<64)-1),1000)
        self.assertEqual((r.counter,r.accumulated_ticks,r.divided_ticks),(0,29999,999))
        r=advance_clock(request_hold(ClockState(),release=True),1000)
        self.assertEqual((r.hold_count,r.interval),(-1,1))

    def test_shared_children_rejected_without_mutating_input(self):
        c=ClockState();s=ClockState(children=(c,c))
        with self.assertRaises(ValueError):advance_clock(s,100)
        self.assertEqual(c.interval,0)
