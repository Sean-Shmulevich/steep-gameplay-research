import struct
import unittest
from engine.action_processor_chain_observation import observe_processor_chain

class ChainObservationTests(unittest.TestCase):
    def setUp(self):
        self.mem=bytearray(65536);self.calls=[]
        self.q(0x1000,0x2000);self.q(0x2028,0x2100);self.q(0x10d0,0x3000)
        self.q(0x4028,0x4100);self.populate(2)
    def q(self,a,v):struct.pack_into('<Q',self.mem,a,v)
    def populate(self,n):
        struct.pack_into('<H',self.mem,0x10da,n)
        for i in range(n):
            child=0x5000+i*0x100;handle=child+0x80;cfg=child+0xa0
            self.q(0x3000+8*i,child);self.q(child,0x4000);self.q(child+16,handle)
            self.q(handle,cfg);self.mem[handle+15]=0x80;self.mem[cfg+0x18]=i%2
    def read(self,a,n):self.calls.append((a,n));return bytes(self.mem[a:a+n])
    def observe(self,read=None):return observe_processor_chain(read or self.read,0x1000,0x2000,0x2100)
    def test_order_bypass_and_duplicate_stages(self):
        r=self.observe();self.assertEqual([s['enabled'] for s in r['stages']],[False,True])
        self.q(0x3008,0x5000)
        self.assertEqual([s['processor'] for s in self.observe()['stages']],[0x5000]*2)
    def test_maximum_budget_and_refusal(self):
        self.populate(8);self.assertEqual(self.observe()['status'],'observed')
        self.assertLessEqual(len(self.calls),104);self.assertLessEqual(sum(n for _,n in self.calls),728)
        struct.pack_into('<H',self.mem,0x10da,9)
        self.assertEqual(self.observe()['status'],'limit')
    def test_null_handle_and_changed_configuration(self):
        self.q(0x5010,0);self.assertEqual(self.observe()['status'],'invalid')
        self.q(0x5010,0x5080);count=0
        def change(a,n):
            nonlocal count
            if a==0x1000:
                count+=1
                if count==2:self.mem[0x50b8]=1
            return self.read(a,n)
        self.assertEqual(self.observe(change),{'status':'unstable'})
    def test_failures_at_each_read(self):
        self.observe();total=len(self.calls)
        for fail in range(1,total+1):
            count=0
            def read(a,n):
                nonlocal count
                count+=1
                if count==fail:raise OSError('fixture')
                return self.read(a,n)
            self.assertEqual(self.observe(read)['status'],'invalid')
