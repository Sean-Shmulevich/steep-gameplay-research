import unittest
from engine.loading_destruction_enqueue import enqueue_loading_destruction
from engine.holder_ring_resize import resize_holder_ring


class LoadingEnqueueTests(unittest.TestCase):
    def test_empty_failed_allocation_still_stages_work(self):
        r=dict(slots=[],storage=None,count=0,tail=0,head=0,capacity=0,owns_storage=True)
        o=dict(ring=r,staged=0);e=[]
        def grow(r,n,p):
            resize_holder_ring(r,n,p,allocate=lambda _:None,copy=lambda *_:self.fail(),free=lambda _:self.fail())
            r['slots']=r['storage']
        result=enqueue_loading_destruction(o,'payload',lock=lambda _:e.append('lock'),unlock=lambda _:e.append('unlock'),grow=grow)
        self.assertFalse(result['inserted']);self.assertEqual(o['staged'],1)
        self.assertEqual(r['count'],0);self.assertEqual(e,['lock','unlock'])

    def test_wrapped_growth_preserves_old_order(self):
        old=['a','b'];r=dict(slots=old,storage=old,count=2,tail=1,head=1,capacity=2,owns_storage=True)
        o=dict(ring=r,staged=2)
        def grow(r,n,p):
            self.assertEqual(n,1026)
            def copy(dst,src,start,count):dst[:count]=[src[(start+i)%len(src)] for i in range(count)]
            resize_holder_ring(r,n,p,allocate=lambda size:[None]*(size//8),copy=copy,free=lambda _:None)
            r['slots']=r['storage']
        enqueue_loading_destruction(o,'new',lock=lambda _:None,unlock=lambda _:None,grow=grow)
        self.assertEqual(r['slots'][:3],['b','a','new']);self.assertEqual(o['staged'],3)

    def test_staged_uint32_wrap(self):
        o=dict(staged=0xffffffff,ring=dict(slots=[None],count=0,tail=0,capacity=1))
        enqueue_loading_destruction(o,None,lock=lambda _:None,unlock=lambda _:None,grow=lambda *_:self.fail())
        self.assertEqual(o['staged'],0);self.assertEqual(o['ring']['count'],1)
