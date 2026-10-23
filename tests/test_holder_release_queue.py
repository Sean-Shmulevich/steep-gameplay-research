import unittest
from engine.holder_release_queue import release_holder_to_queue


class HolderReleaseQueueTests(unittest.TestCase):
    def run_case(self, growth, *, capacity=0, count=0, tail=0, mode=1):
        h=dict(status=0,payload='payload')
        ring=dict(slots=[None]*capacity,count=count,tail=tail,head=0,capacity=capacity)
        reg=dict(mode=mode,ring=ring);events=[]
        def grow(r,size,flag):
            self.assertEqual(h['status'],1<<24)
            events.append(('grow',size,flag));growth(r)
        result=release_holder_to_queue(h,reg,global_suppress=False,
            lock=lambda _:events.append('lock'),unlock=lambda _:events.append('unlock'),grow=grow,
            cleanup=lambda *_:self.fail('unexpected cleanup'),classify_thread=lambda:0,
            post_unlock=lambda _:events.append('service'))
        return h,ring,events,result

    def test_failed_growth_retains_flag_without_enqueue_but_can_run_service(self):
        h,r,e,result=self.run_case(lambda _:None)
        self.assertEqual(h['status'],1<<24);self.assertEqual(r['count'],0)
        self.assertFalse(result['enqueued'])
        self.assertEqual(e,['lock',('grow',0x4000,True),'unlock','service'])

    def test_growth_reloads_replaced_storage_and_header(self):
        def growth(r):r.update(slots=[None]*2,capacity=2,count=1,tail=1)
        h,r,e,result=self.run_case(growth)
        self.assertTrue(result['enqueued']);self.assertIs(r['slots'][1],h)
        self.assertEqual((r['count'],r['tail']),(2,0))

    def test_existing_capacity_does_not_grow(self):
        h,r,e,result=self.run_case(lambda _:self.fail(),capacity=2,count=1,tail=1,mode=0)
        self.assertEqual(e,['lock','unlock']);self.assertTrue(result['enqueued'])
        self.assertFalse(result['growth_requested'])

    def test_repeated_release_after_failed_growth_does_not_retry_insertion(self):
        h,r,_,_=self.run_case(lambda _:None)
        events=[]
        result=release_holder_to_queue(h,dict(mode=1,ring=r),global_suppress=False,
            lock=lambda _:events.append('lock'),unlock=lambda _:events.append('unlock'),
            grow=lambda *_:self.fail('queued flag bypasses growth'),cleanup=lambda *_:self.fail(),
            classify_thread=lambda:self.fail(),post_unlock=lambda _:self.fail())
        self.assertEqual(result['route'],'no_action');self.assertFalse(result['enqueued'])
        self.assertEqual(events,['lock','unlock'])
