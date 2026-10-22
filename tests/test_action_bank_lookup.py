import unittest
from engine.action_bank_lookup import ActionLayer as L, select_action

class ActionBankTests(unittest.TestCase):
    def test_reverse_records_forward_groups(self):
        result=select_action(((L('older','old'),L('newer',None)),(L('later','late'),),()))
        self.assertEqual(result.action,'old');self.assertEqual(result.visited,('newer','older'))
    def test_miss_barrier_stops_all_groups(self):
        result=select_action(((L('older','old'),L('barrier',None,True)),(L('later','late'),),()))
        self.assertIsNone(result.action);self.assertTrue(result.stopped_on_miss)
        self.assertEqual(result.visited,('barrier',))
    def test_hit_precedes_barrier(self):
        result=select_action(((),(L('hit','selected',True),),()))
        self.assertEqual(result.action,'selected');self.assertFalse(result.stopped_on_miss)
    def test_empty_and_late_group(self):
        self.assertEqual(select_action(((),(),())).visited,())
        self.assertEqual(select_action(((),(),(L('last','found'),))).action,'found')
    def test_count_contract(self):
        with self.assertRaises(ValueError):select_action(((),()))
