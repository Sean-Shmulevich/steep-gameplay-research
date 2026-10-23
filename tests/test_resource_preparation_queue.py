import unittest
from engine.resource_preparation_queue import prepare_resource_queue


class ResourcePreparationQueueTests(unittest.TestCase):
    def setup_registry(self,key=7,payload='current'):
        h=dict(token=7,status=0,payload=payload)
        triple=dict(key=key,queued_record='old',holder=h)
        r=dict(published=1,ring=dict(slots=[triple,triple],capacity=2,count=1,head=0))
        return r,h

    def test_dispatches_current_record_and_defers_callback_published_budget(self):
        r,h=self.setup_registry();seen=[]
        def dispatch(p):
            seen.append(p);r['published']=1;r['ring']['count']+=1
        result=prepare_resource_queue(r,lock=lambda _:None,unlock=lambda _:None,dispatch_current=dispatch)
        self.assertEqual(seen,['current']);self.assertEqual(h['status'],1<<31)
        self.assertEqual(result,dict(captured=1,consumed=1,dispatched=1))
        self.assertEqual((r['published'],r['ring']['count']),(1,1))

    def test_stale_key_skips_and_null_current_only_marks(self):
        for key,payload,expected in [(8,'current',0),(7,None,1<<31)]:
            r,h=self.setup_registry(key,payload)
            prepare_resource_queue(r,lock=lambda _:None,unlock=lambda _:None,dispatch_current=lambda _:self.fail())
            self.assertEqual(h['status'],expected)

    def test_shortage_is_not_successful_drain(self):
        r,h=self.setup_registry();r['ring']['count']=0;events=[]
        with self.assertRaises(ValueError):
            prepare_resource_queue(r,lock=lambda _:events.append('lock'),unlock=lambda _:events.append('unlock'),dispatch_current=lambda _:self.fail())
        self.assertEqual(events,['lock']);self.assertEqual(r['published'],0)
