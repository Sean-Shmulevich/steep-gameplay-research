import unittest
from engine.examples.history_action_freshness import inspect
from engine.history_action_bench import inspect_history_action


class HistoryActionBenchTests(unittest.TestCase):
    def test_hold_can_fire_without_new_history(self):
        rows=inspect()['observations']
        first,second,released=rows[1],rows[2],rows[4]
        self.assertFalse(first['active'])
        self.assertTrue(second['active'])
        self.assertTrue(second['reused_history'])
        self.assertEqual(first['history_timestamp'],second['history_timestamp'])
        self.assertEqual(second['producer_sequence'],1)
        self.assertFalse(released['active'])
        self.assertFalse(released['reused_history'])
        self.assertEqual(released['start_time'],100)

    def test_empty_history_is_not_labeled_as_produced(self):
        result=inspect_history_action([dict(kind='evaluate',clocks=[],ownership=[False,False])],
            channel=1,alternate_center=False,primary=[0,1,0,0],secondary=[1,0,0,0],
            reference=[0,1,0,0],direction_kind=0,magnitude_threshold=.5,
            mode=1,hold_delay=.1,repeat_delay=0)
        self.assertFalse(result['observations'][0]['producer_ran'])
        self.assertFalse(result['observations'][0]['active'])
