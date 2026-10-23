import unittest
from engine.command_attachment_acquisition import acquire_attachment


class AttachmentAcquisitionTests(unittest.TestCase):
    def test_pointer_mismatch_still_reads_old_count_before_retry(self):
        reads=iter(['a','b','b','b']);events=[];counts={'a':1,'b':2}
        def count(p):events.append(('count',p));return counts[p]
        def cas(p,old,new):events.append(('cas',p));counts[p]=new;return old
        result=acquire_attachment(read_source=lambda:next(reads),read_count=count,compare_exchange=cas)
        self.assertEqual(result,'b');self.assertEqual(events,[('count','a'),('count','b'),('cas','b')])
        self.assertEqual(counts,{'a':1,'b':3})

    def test_source_change_after_second_read_does_not_prevent_old_acquisition(self):
        source=['a'];counts={'a':1,'b':1}
        def count(p):source[0]='b';return counts[p]
        def cas(p,old,new):counts[p]=new;return old
        result=acquire_attachment(read_source=lambda:source[0],read_count=count,compare_exchange=cas)
        self.assertEqual((result,source[0]),('a','b'));self.assertEqual(counts,{'a':2,'b':1})

    def test_failed_cas_restarts_and_can_find_null_source(self):
        source=['a'];events=[]
        def cas(p,old,new):source[0]=None;events.append('cas');return old+1
        self.assertIsNone(acquire_attachment(read_source=lambda:source[0],read_count=lambda _:1,compare_exchange=cas))
        self.assertEqual(events,['cas'])

    def test_zero_is_not_rejected_and_uint32_wrap_is_preserved(self):
        for old in (0,0xffffffff):
            events=[]
            result=acquire_attachment(read_source=lambda:'a',read_count=lambda _:old,
                compare_exchange=lambda p,o,n:events.append(n) or o)
            self.assertEqual(result,'a');self.assertEqual(events,[(old+1)&0xffffffff])
