import unittest
from engine.action_processor_chain import process_chain

class ProcessorChainTests(unittest.TestCase):
    def test_order_and_bypass_publication(self):
        calls=[]
        def child(i,value):
            calls.append((i,value))
            return bytes((b+i+1)%256 for b in value)
        r=process_chain(bytes(16),[True,False,None],child)
        self.assertEqual(calls,[(0,bytes(16)),(2,b'\1'*16)])
        self.assertEqual(r.output,b'\4'*16)
        self.assertEqual(r.stages[1].raw,b'\1'*16)
        self.assertEqual(r.stages[1].published,b'\1'*16)
        self.assertFalse(r.stages[1].invoked)
    def test_empty_and_all_bypassed_preserve_all_bits(self):
        raw=bytes(range(16))
        def forbidden(*args):raise AssertionError('bypassed callback ran')
        for flags in ([],[False]*3):
            self.assertEqual(process_chain(raw,flags,forbidden).output,raw)
    def test_unknown_child_result_is_not_defaulted(self):
        with self.assertRaises(ValueError):process_chain(bytes(16),[None],lambda *a:b'')
    def test_noncommuting_child_order(self):
        def child(i,v):return v[::-1] if i==0 else bytes((b+idx)%256 for idx,b in enumerate(v))
        raw=bytes(range(16))
        self.assertEqual(process_chain(raw,[True,True],child).output,bytes([15])*16)
