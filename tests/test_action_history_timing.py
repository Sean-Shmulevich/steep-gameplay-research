import unittest
from engine.action_history_timing import advance_history_timing


class HistoryTimingTests(unittest.TestCase):
    def run_case(self, **changes):
        args=dict(current=True,previous=False,mode=1,start_time=0,repeat_time=0,
                  hold_delay=.1,repeat_delay=0,read_clock=lambda:100)
        args.update(changes)
        return advance_history_timing(**args)

    def test_hold_starts_without_firing_then_reaches_inclusive_threshold(self):
        first=self.run_case()
        self.assertFalse(first['active'])
        self.assertEqual(first['start_time'],100)
        self.assertFalse(self.run_case(previous=True,start_time=100,read_clock=lambda:199)['active'])
        self.assertTrue(self.run_case(previous=True,start_time=100,read_clock=lambda:200)['active'])

    def test_repeat_uses_second_clock_read_and_retains_timestamp_on_release(self):
        times=iter((200,205))
        result=self.run_case(previous=True,start_time=100,repeat_time=190,
                             repeat_delay=.02,read_clock=lambda:next(times))
        self.assertEqual(result['clock_reads'],[200,205])
        self.assertFalse(result['active'])
        self.assertEqual(result['repeat_time'],190)
        released=self.run_case(current=False,previous=True,start_time=100,repeat_time=190)
        self.assertEqual(released['clock_reads'],[])
        self.assertEqual(released['start_time'],100)
        self.assertEqual(released['repeat_time'],190)

    def test_zero_delay_edges_and_unsigned_elapsed(self):
        self.assertTrue(self.run_case(hold_delay=0)['active'])
        self.assertEqual(self.run_case(mode=0)['clock_reads'],[])
        self.assertTrue(self.run_case(mode=2,current=False,previous=True)['active'])
        self.assertFalse(self.run_case(mode=3)['active'])
        self.assertTrue(self.run_case(previous=True,start_time=(1<<64)-50,read_clock=lambda:50)['active'])
        with self.assertRaises(ValueError):self.run_case(hold_delay=-1)
