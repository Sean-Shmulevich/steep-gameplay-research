import unittest
from engine.command_counter_transfer import replay_counter_transfers

class CommandCounterTests(unittest.TestCase):
    def test_submission_after_exchange_remains_deferred(self):
        initial={'A':[2,3],'B':[7,11]}
        result=replay_counter_transfers(initial,[('exchange','A',None),('submit','A',5),
            ('add','A',None),('exchange','B',None),('add','B',None)])
        self.assertEqual(result['counters'],{'A':[5,5],'B':[18,0]})
        self.assertEqual(initial,{'A':[2,3],'B':[7,11]})
        self.assertEqual(result['trace'][0]['pending'],{'A':3})
        self.assertFalse(result['native_concurrency_proved'])

    def test_submission_before_exchange_transfers_in_current_pass(self):
        r=replay_counter_transfers({'A':[2,3],'B':[0,0]},[
            ('submit','A',5),('exchange','A',None),('add','A',None)])
        self.assertEqual(r['counters']['A'],[10,0])

    def test_wrapping_and_nontransactional_pair_boundary(self):
        r=replay_counter_transfers({'A':[0xffffffff,1],'B':[4,5]},[
            ('exchange','A',None),('add','A',None),('exchange','B',None)])
        self.assertEqual(r['counters'],{'A':[0,0],'B':[4,0]})
        self.assertEqual(r['pending'],{'B':5})

    def test_invalid_transfer_sequences_and_inputs(self):
        for events in [[('add','A',None)], [('exchange','A',None)]*2,
                       [('submit','B',True)],[('exchange','X',None)]]:
            with self.assertRaises(ValueError):replay_counter_transfers({'A':[0,0],'B':[0,0]},events)
