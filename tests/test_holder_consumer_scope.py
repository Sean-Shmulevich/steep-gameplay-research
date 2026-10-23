import unittest
from engine.holder_consumer_scope import run_holder_consumer


class ConsumerScopeTests(unittest.TestCase):
    def setup_state(self):
        return dict(processing=0,ring={'count':1}),dict(active=0,word=0xffffffff,limit=0),dict(pending=2,published=0xffffffff,semaphore=0xffffffff)

    def test_normal_handoff_and_lock_order(self):
        r,c,w=self.setup_state();e=[]
        def process(reg):reg['ring']['count']-=1
        result=run_holder_consumer(r,c,w,lock=lambda x:e.append(('lock',x)),unlock=lambda x:e.append(('unlock',x)),process_one=process,signal=lambda:e.append(('signal',)))
        self.assertTrue(result['signaled']);self.assertEqual(w,dict(pending=0,published=1,semaphore=0))
        self.assertEqual(c,dict(active=0,word=0xff800000,limit=0x3fffffff))
        self.assertEqual(e[-3:],[('unlock','coordination'),('unlock','global_1d8'),('unlock','registry_b8')])

    def test_reentrant_call_only_enters_and_leaves_two_guards(self):
        r,c,w=self.setup_state();nested=[]
        def forbidden(*_):self.fail()
        def process(reg):
            nested.append(run_holder_consumer(r,c,w,lock=lambda _:None,unlock=lambda _:None,process_one=forbidden,signal=forbidden))
            self.assertEqual(r['processing'],1);reg['ring']['count']=0
        run_holder_consumer(r,c,w,lock=lambda _:None,unlock=lambda _:None,process_one=process,signal=lambda:None)
        self.assertFalse(nested[0]['entered'])

    def test_zero_pending_does_not_touch_semaphore(self):
        r,c,w=self.setup_state();r['ring']['count']=0;w['pending']=0;w['semaphore']=5
        run_holder_consumer(r,c,w,lock=lambda _:None,unlock=lambda _:None,process_one=lambda _:self.fail(),signal=lambda:self.fail())
        self.assertEqual(w['semaphore'],5)
