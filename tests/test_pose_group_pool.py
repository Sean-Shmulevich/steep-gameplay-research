import unittest
from engine.pose_group_pool import acquire_pose_group_storage


class PoolTests(unittest.TestCase):
    def fixture(self):
        return dict(free_head=0,used=0,current=1000,chunk_index=0,slot_index=0,
                    per_chunk=2,alignment=16,chunk_count=1,chunk_capacity=2,
                    chunks=[1000,0])

    def acquire(self,p,**overrides):
        services=dict(read_next=lambda t:0,allocate=lambda *a:3000,
                      grow=lambda p,c:None)
        services.update(overrides)
        return acquire_pose_group_storage(p,**services)

    def test_free_chain_precedes_current_chunk(self):
        p=self.fixture();p.update(free_head=9000,used=0xffffffff)
        self.assertEqual(self.acquire(p,read_next=lambda t:9008),9000)
        self.assertEqual((p['free_head'],p['used'],p['slot_index']),(9008,0,0))

    def test_existing_chunks_then_allocate(self):
        p=self.fixture();p.update(chunk_count=2,chunks=[1000,2000])
        self.assertEqual([self.acquire(p) for _ in range(4)],[1000,1168,2000,2168])
        self.assertEqual((p['current'],p['slot_index'],p['chunk_index']),(0,0,0))
        def grow(p,c):p['chunks'].extend([0]*(c-len(p['chunks'])));p['chunk_capacity']=c
        self.assertEqual(self.acquire(p,grow=grow),3000)
        self.assertEqual(p['chunks'][:3],[1000,2000,3000])

    def test_growth_and_allocator_arguments(self):
        p=self.fixture();p.update(current=0,chunk_count=0,chunk_capacity=0,chunks=[])
        calls=[]
        def allocate(*args):calls.append(args);return 5000
        def grow(p,c):calls.append(c);p['chunk_capacity']=c;p['chunks']=[0]*c
        self.assertEqual(self.acquire(p,allocate=allocate,grow=grow),5000)
        self.assertEqual(calls,[(336,16,47),8])

    def test_null_allocator_result_is_not_given_invented_failure_policy(self):
        p=self.fixture();p.update(current=0,chunk_count=0)
        self.assertEqual(self.acquire(p,allocate=lambda *a:0),0)
        self.assertEqual((p['chunk_count'],p['used'],p['slot_index']),(1,1,1))
