from dataclasses import replace
import unittest
from engine.clock_tree import ClockState, advance_clock
from engine.action_history_timing import advance_history_timing


class HistoryActionClockTests(unittest.TestCase):
    def evaluate(self, clock, previous, start):
        return advance_history_timing(current=True,previous=previous,mode=1,
            start_time=start,repeat_time=0,hold_delay=.1,repeat_delay=0,
            read_clock=lambda:clock.divided_ticks)

    def test_hold_and_scale_change_timer_through_divided_ticks(self):
        clock=ClockState()
        first=self.evaluate(clock,False,0)
        self.assertFalse(first['active'])
        clock=advance_clock(clock,50)
        self.assertEqual(clock.divided_ticks,50)
        self.assertFalse(self.evaluate(clock,True,0)['active'])
        held=advance_clock(replace(clock,hold_count=1),500)
        self.assertEqual(held.divided_ticks,50)
        self.assertFalse(self.evaluate(held,True,0)['active'])
        scaled=advance_clock(replace(held,hold_count=0,scale_enabled=True,scale=2),25)
        self.assertEqual(scaled.divided_ticks,100)
        self.assertTrue(self.evaluate(scaled,True,0)['active'])

    def test_interval_change_without_accumulation_does_not_complete_hold(self):
        clock=advance_clock(ClockState(),50)
        advanced=advance_clock(clock,200,accumulate=False)
        self.assertNotEqual(advanced.interval,clock.interval)
        self.assertEqual(advanced.divided_ticks,clock.divided_ticks)
        self.assertFalse(self.evaluate(advanced,True,0)['active'])
