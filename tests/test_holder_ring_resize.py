import unittest
from engine.holder_ring_resize import resize_holder_ring


class HolderRingResizeTests(unittest.TestCase):
    def test_wrap_preserves_order_and_releases_owned_storage(self):
        old=[10,11,12,13];r=dict(storage=old,capacity=4,count=3,head=3,tail=2,owns_storage=True)
        events=[]
        def copy(dst,src,start,count):dst[:count]=[src[(start+i)%len(src)] for i in range(count)]
        resize_holder_ring(r,8,True,allocate=lambda size:[None]*(size//8),copy=copy,free=lambda s:events.append(s))
        self.assertEqual(r['storage'][:3],[13,10,11]);self.assertEqual((r['head'],r['tail'],r['count']),(0,3,3))
        self.assertEqual(events,[old])

    def test_empty_allocation_failure_leaves_zero_capacity(self):
        r=dict(storage=None,capacity=0,count=0,head=0,tail=0,owns_storage=True)
        resize_holder_ring(r,8,True,allocate=lambda _:None,copy=lambda *_:self.fail(),free=lambda _:self.fail())
        self.assertEqual(r['capacity'],0);self.assertIsNone(r['storage'])

    def test_nonempty_null_allocation_reaches_copy_before_header_reset(self):
        old=[1];r=dict(storage=old,capacity=1,count=1,head=0,tail=0,owns_storage=True)
        def copy(dst,*_):
            self.assertIsNone(dst);raise ValueError('null destination')
        with self.assertRaises(ValueError):
            resize_holder_ring(r,8,True,allocate=lambda _:None,copy=copy,free=lambda _:self.fail())
        self.assertIs(r['storage'],old);self.assertEqual(r['count'],1)

    def test_same_capacity_clear_keeps_storage_and_ownership(self):
        r=dict(storage=[1],capacity=1,count=1,head=0,tail=0,owns_storage=False)
        resize_holder_ring(r,1,False,allocate=lambda _:self.fail(),copy=lambda *_:self.fail(),free=lambda _:self.fail())
        self.assertEqual(r['count'],0);self.assertFalse(r['owns_storage'])
