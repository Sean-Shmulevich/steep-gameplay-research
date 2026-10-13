import unittest
from engine.trace import Trace

class TraceTests(unittest.TestCase):
    def test_overflow_is_nonwrapping_and_explicit(self):
        t=Trace(2)
        for i in range(5):t.emit('event',tick=i)
        s=t.snapshot();self.assertEqual([r['tick'] for r in s['records']],[0,1])
        self.assertEqual(s['dropped'],3);self.assertFalse(s['complete'])
    def test_restore_continues_sequence_and_copies(self):
        t=Trace(5);t.emit('start');s=t.snapshot();other=Trace.restore(s);other.emit('end')
        self.assertEqual(other.records[-1]['sequence'],1);self.assertEqual(len(s['records']),1)
    def test_invalid_emit_does_not_consume_sequence(self):
        t=Trace()
        with self.assertRaises(ValueError):t.emit('bad',time=float('nan'))
        self.assertEqual(t.attempted,0)
    def test_inconsistent_accounting_rejected(self):
        t=Trace();s=t.snapshot();s['dropped']=1
        with self.assertRaises(ValueError):Trace.restore(s)
