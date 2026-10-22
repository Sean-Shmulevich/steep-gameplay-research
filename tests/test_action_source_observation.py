import struct
import unittest
from engine.action_source_observation import observe_action_source

class ActionSourceObservationTests(unittest.TestCase):
    def setUp(self):
        self.mem=bytearray(0x100000);self.calls=[]
        self.q(0x1000,0x2000);self.q(0x2010,0x2100)
        self.q(0x1010,0x5000);self.q(0x10b0,0x7000);self.q(0x10b8,0x4000)
        self.q(0x5000,0x10000);self.q(0x6000,0x20000)
        self.q(0x7000,0x8000);self.q(0x8028,0x8100);self.q(0x7010,0x9000)
        self.q(0x9000,0xa000);struct.pack_into('<i',self.mem,0x900c,-1)
        self.mem[0xa018]=1
        self.mem[0x101f0:0x10200]=bytes(range(16))
    def q(self,a,v):struct.pack_into('<Q',self.mem,a,v)
    def read(self,a,n):self.calls.append((a,n));return bytes(self.mem[a:a+n])
    def observe(self,read=None,family='vector'):
        return observe_action_source(read or self.read,0x1000,0x2000,0x2100,family,0x6000)
    def test_vector_gate_and_processor_configuration(self):
        d=self.observe()['details']
        self.assertEqual(d['derived_source_bits'],bytes(range(16)).hex())
        self.assertTrue(d['processing_enabled']);self.assertFalse(d['ownership_blocked'])
        self.q(0x2f050,0x5555)
        d=self.observe()['details'];self.assertTrue(d['ownership_blocked'])
        self.assertEqual(d['derived_source_bits'],'00'*16)
        self.assertEqual(d['cached_bits'],bytes(range(16)).hex())
    def test_mask_top_and_bypass(self):
        self.q(0x10248,0xb000);struct.pack_into('<H',self.mem,0x10252,2)
        self.q(0xb000,7);self.q(0xb008,8);self.mem[0xa018]=0
        d=self.observe()['details'];self.assertTrue(d['mask_blocked']);self.assertFalse(d['processing_enabled'])
        self.q(0xb008,0)
        self.assertFalse(self.observe()['details']['mask_blocked'])
        struct.pack_into('<i',self.mem,0x900c,0)
        d=self.observe()['details'];self.assertTrue(d['processing_enabled']);self.assertEqual(d['processor_configuration'],0)
    def test_directional_ids_and_budget(self):
        struct.pack_into('<8I',self.mem,0x4030,*range(8))
        d=self.observe(family='directional')['details'];self.assertEqual(d['query_ids'],list(range(8)))
        self.assertNotIn((0x6000,8),self.calls)
        self.assertLessEqual(len(self.calls),64);self.assertLessEqual(sum(n for _,n in self.calls),4096)
    def test_each_read_failure_and_root_mutation(self):
        self.observe();count=len(self.calls)
        for fail in range(1,count+1):
            i=0
            def fault(a,n):
                nonlocal i
                i+=1
                if i==fail:raise OSError('fixture')
                return self.read(a,n)
            self.assertEqual(self.observe(fault)['status'],'invalid')
        i=0
        def change(a,n):
            nonlocal i
            if a==0x1000:
                i+=1
                if i==2:self.mem[0xa018]=0
            return self.read(a,n)
        self.assertEqual(self.observe(change),{'status':'unstable'})
    def test_unknown_kind_and_wrong_type(self):
        struct.pack_into('<I',self.mem,0x4030,4)
        self.assertEqual(self.observe()['status'],'unsupported')
        self.q(0x2010,0x9999)
        self.assertEqual(self.observe()['status'],'unsupported')
    def test_unused_handle_bits_do_not_reject_but_sign_change_does(self):
        for sign_change,expected in ((False,'observed'),(True,'unstable')):
            self.setUp()
            count=0
            def change(a,n):
                nonlocal count
                if a==0x1000:
                    count+=1
                    if count==2:
                        self.mem[0x9008]=7
                        struct.pack_into('<I',self.mem,0x900c,0x7ffffffe if sign_change else 0x80000002)
                return self.read(a,n)
            self.assertEqual(self.observe(change)['status'],expected)
