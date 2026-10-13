import unittest
from engine.graph import read_producer,update
class GraphTests(unittest.TestCase):
    def test_ready_survives_cached_then_clears_after_full(self):
        state={};calls=[]
        def produce():calls.append(1);return {'x':len(calls)}
        self.assertEqual(read_producer(state,'g','x',produce),1)
        seen=[]
        self.assertEqual(update(state,.1,{'byte_threshold':2},lambda dt:None,[lambda dt:seen.append(dt)])['path'],'cached_callbacks')
        def evaluate(dt):
            self.assertAlmostEqual(dt,.2)
            self.assertEqual(read_producer(state,'g','x',produce),1)
        self.assertEqual(update(state,.1,{'byte_threshold':2},evaluate,[lambda dt:None])['path'],'full_evaluation')
        self.assertEqual(read_producer(state,'g','x',produce),2)
    def test_counter_wrap_and_pending_gate(self):
        state={'byte_counter':255}
        result=update(state,.01,{'byte_threshold':1},lambda dt:None,[lambda dt:None])
        self.assertEqual(result['path'],'cached_callbacks');self.assertEqual(state['byte_counter'],0)
        result=update(state,.01,{'byte_threshold':255,'pending_count':1},lambda dt:None,[lambda dt:None])
        self.assertEqual(result['path'],'full_evaluation')
