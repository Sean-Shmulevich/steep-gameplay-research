import struct
import unittest
from engine.skeleton_post_observation import capture_skeleton_post_membership


class SkeletonPostObservationTests(unittest.TestCase):
    def setUp(self):
        self.base=0x100000;self.mem=bytearray(0x40000)
        self.entity=self.base+0x1000;self.world=self.base+0x2000;self.graph=self.base+0x5000
        self.source=self.base+0x18000;self.storage=self.base+0x19000;self.skeleton=self.base+0x20000
        self.image=0x140000000
        self.put(self.entity+0x60,'<Q',self.world)
        self.put(self.world+0x1038,'<Q',self.graph);self.put(self.graph,'<Q',self.world)
        self.put(self.graph+0x7930,'<Q',self.image+0xd5bff0)
        self.put(self.world+0x4f0,'<QiI',self.source,1,1)
        self.put(self.graph+0x7908,'<Qii',self.storage,0,2)
        self.put(self.source,'<Q',self.skeleton);self.put(self.storage,'<QQ',self.skeleton,self.skeleton)
        self.put(self.skeleton,'<QQQ',self.image+0x1f1e598,0,self.entity)
    def put(self,a,f,*v):
        b=struct.pack(f,*v);self.mem[a-self.base:a-self.base+len(b)]=b
    def read(self,plan):
        return [bytes(self.mem[a-self.base:a-self.base+n]) for a,n in plan]
    def capture(self,read=None):
        return capture_skeleton_post_membership(read or self.read,self.entity,self.world,self.image,
                                               [(self.entity+0x60,struct.pack('<Q',self.world))])
    def test_exact_skeleton_owner_and_stale_storage(self):
        r=self.capture();self.assertTrue(r['source_membership_observed'])
        self.assertEqual(r['player_skeleton_source_matches'][0]['storage_indices'],[0,1])
        self.assertEqual(r['player_skeleton_source_matches'][0]['unclaimed_prefix_indices'],[])
        self.assertFalse(r['callback_execution_established'])
    def test_empty_source_does_not_promote_stale_storage(self):
        self.put(self.world+0x4f0,'<QiI',self.source,0,1)
        self.put(self.graph+0x7910,'<i',1)
        r=self.capture();self.assertFalse(r['source_membership_observed'])
        self.assertEqual(r['remaining_to_claim'],1)
    def test_wrong_owner_and_callback(self):
        self.put(self.skeleton+16,'<Q',self.entity+8)
        self.assertFalse(self.capture()['source_membership_observed'])
        self.put(self.graph+0x7930,'<Q',0)
        with self.assertRaisesRegex(ValueError,'callback mismatch'):self.capture()
    def test_changed_source_rejected(self):
        seen=0
        def read(plan):
            nonlocal seen
            out=self.read(plan)
            for i,(a,n) in enumerate(plan):
                if a==self.source:
                    seen+=1
                    if seen==2:out[i]=bytes(n)
            return out
        with self.assertRaisesRegex(ValueError,'changed'):self.capture(read)
