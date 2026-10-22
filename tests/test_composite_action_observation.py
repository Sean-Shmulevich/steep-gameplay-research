import struct
import unittest
from engine.composite_action_observation import observe_composite

class CompositeObservationTests(unittest.TestCase):
    def setUp(self):
        self.mem=bytearray(65536);self.calls=[]
        self.q(0x1000,0x2000);self.q(0x2010,0x2100)
        self.q(0x10b0,0x3000);self.q(0x10b8,0x4000)
        self.q(0x3028,0x5000);self.q(0x6010,0x6100)
        self.mem[0x1050:0x1084]=b'P'*52
        self.populate(2)
    def q(self,a,n):struct.pack_into('<Q',self.mem,a,n)
    def populate(self,n):
        struct.pack_into('<H',self.mem,0x10c2,n)
        for i in range(n):
            child=0x7000+i*0x100;record=0x9000+i*0x20
            self.q(0x4000+8*i,child);self.q(child,0x6000)
            self.mem[child+0x30]=i%2;self.mem[child+0x50:child+0x84]=bytes([i])*52
            self.q(0x5000+8*i,record);struct.pack_into('<I',self.mem,record+16,i)
    def read(self,a,n):self.calls.append((a,n));return bytes(self.mem[a:a+n])
    def observe(self,read=None):return observe_composite(read or self.read,0x1000,0x2000,0x2100)
    def test_children_modes_and_final_mode_not_read(self):
        r=self.observe();self.assertEqual(r.status,'observed')
        self.assertEqual([c.mode for c in r.children],[0,None])
        self.assertEqual(r.children[1].payload,b'\1'*52)
        self.assertEqual(r.children[0].callback,0x6100)
        self.assertNotIn((0x5008,8),self.calls)
    def test_maximum_budget_and_count_refusal(self):
        self.populate(16);self.assertEqual(self.observe().status,'observed')
        self.assertLessEqual(len(self.calls),136)
        self.assertLessEqual(sum(n for _,n in self.calls),5600)
        struct.pack_into('<H',self.mem,0x10c2,17)
        self.calls=[];self.assertEqual(self.observe().status,'limit')
        self.assertNotIn((0x4000,136),self.calls)
    def test_type_and_configuration_refusal(self):
        self.q(0x2010,0x2200);self.assertEqual(self.observe().status,'unsupported')
        self.q(0x2010,0x2100);self.q(0x10b0,0)
        self.assertEqual(self.observe().status,'unavailable')
    def test_every_read_failure_and_changed_mode(self):
        self.observe();count=len(self.calls)
        for fail in range(1,count+1):
            i=0
            def fault(a,n):
                nonlocal i
                i+=1
                if i==fail:raise OSError('fixture')
                return self.read(a,n)
            self.assertEqual(self.observe(fault).status,'invalid')
        i=0
        def change(a,n):
            nonlocal i
            if a==0x1000:
                i+=1
                if i==2:self.mem[0x9010]=1
            return self.read(a,n)
        r=self.observe(change);self.assertEqual((r.status,r.children),('unstable',()))
    def test_empty_and_null_child(self):
        self.populate(0);self.assertEqual(self.observe().children,())
        self.populate(1);self.q(0x4000,0)
        self.assertEqual(self.observe().status,'invalid')
