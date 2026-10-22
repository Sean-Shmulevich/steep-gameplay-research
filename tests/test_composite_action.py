import unittest
from engine.composite_action import ChildSample, evaluate_composite

class CompositeActionTests(unittest.TestCase):
    def evaluate(self,statuses,modes):
        self.calls=[]
        def child(i):
            self.calls.append(('child',i))
            return ChildSample(statuses[i],bytes([i+1])*52)
        def mode(i):
            self.calls.append(('mode',i))
            return modes[i]
        return evaluate_composite(len(statuses),child,mode,b'P'*52)
    def test_rejection_retains_payload_and_stops_evaluation(self):
        r=self.evaluate([0,1],[1])
        self.assertEqual((r.status,r.payload,r.selected_index),(0,b'P'*52,None))
        self.assertEqual(self.calls,[('child',0),('mode',0)])
    def test_early_selection_normalizes_status(self):
        r=self.evaluate([255,0],[0])
        self.assertEqual((r.status,r.selected_index,r.payload),(1,0,b'\1'*52))
        self.assertEqual(r.visited,(0,))
    def test_last_child_copies_even_zero_and_preserves_status_byte(self):
        for status in (0,2,255):
            r=self.evaluate([1,status],[1])
            self.assertEqual((r.status,r.selected_index,r.payload),(status,1,b'\2'*52))
            self.assertEqual(self.calls,[('child',0),('mode',0),('child',1)])
    def test_unknown_mode_continues_and_empty_preserves(self):
        for mode in (2,0xffffffff):
            self.assertEqual(self.evaluate([1,0],[mode]).selected_index,1)
        r=self.evaluate([],[])
        self.assertEqual((r.status,r.payload,r.visited),(0,b'P'*52,()))
    def test_payload_is_uninterpreted(self):
        bits=bytes(range(52))
        r=evaluate_composite(1,lambda i:ChildSample(7,bits),None,b'P'*52)
        self.assertEqual((r.status,r.payload),(7,bits))
