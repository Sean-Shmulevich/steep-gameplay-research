import unittest
from engine.frame_clock_policy import select_interval


class FrameClockPolicyTests(unittest.TestCase):
    def test_fixed_capped_and_unknown(self):
        self.assertEqual(select_interval(elapsed_seconds=1, mode=0, rate=4)['input_ms'], 250)
        self.assertEqual(select_interval(elapsed_seconds=1, mode=2, table=(.25,))['input_ms'], 250)
        self.assertEqual(select_interval(elapsed_seconds=1, mode=7)['input_ms'], 1000)
        self.assertGreater(select_interval(elapsed_seconds=-1, mode=7)['interval_seconds'], 0)

    def test_table_transition_and_counter_preservation(self):
        args=dict(mode=1,table=(.5,.25,.125),table_index=1)
        r=select_interval(elapsed_seconds=1, stable_count=11, **args)
        self.assertEqual((r['table_index'],r['stable_count']), (0,0))
        r=select_interval(elapsed_seconds=.1, stable_count=10, **args)
        self.assertEqual((r['table_index'],r['stable_count']), (1,11))
        r=select_interval(elapsed_seconds=.1, stable_count=11, **args)
        self.assertEqual((r['table_index'],r['stable_count']), (2,11))
        r=select_interval(elapsed_seconds=1, mode=1,table=(.5,),stable_count=11)
        self.assertEqual(r['stable_count'],11)

    def test_history_last_slot_is_not_in_sum(self):
        r=select_interval(elapsed_seconds=9,mode=3,history=[.25]*16,history_index=15)
        self.assertEqual((r['interval_seconds'],r['history_index'],r['neighboring_low_word_float_write']),(.25,0,9))
        self.assertEqual(r['history'][15],9)

    def test_input_guards(self):
        for kw in [dict(mode=True),dict(mode=0,rate=0),dict(mode=3,history_index=16),dict(mode=1,table=())]:
            with self.assertRaises(ValueError): select_interval(elapsed_seconds=1,**kw)
