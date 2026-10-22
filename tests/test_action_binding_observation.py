import struct
import unittest
from engine.action_binding_observation import observe_action_binding

class BindingObservationTests(unittest.TestCase):
    def setUp(self):
        self.mem=bytearray(65536);self.calls=[]
        self.q(0x1020,0x2000);struct.pack_into('<H',self.mem,0x102a,1)
        self.q(0x2000,0x3000);self.q(0x3090,0x4000);struct.pack_into('<H',self.mem,0x309a,2)
        self.q(0x4000,0x5000);self.q(0x4008,0x5100)
        for binding,descriptor,leaf,action in ((0x5000,0x6000,0x7000,0x8000),(0x5100,0x6100,0x7100,0x8100)):
            self.q(binding+0x28,descriptor);self.q(descriptor+8,leaf|1)
            self.q(leaf,0);self.q(leaf+8,0x76);self.q(leaf+16,action)
            self.q(action,0x9000);self.mem[action+0x60:action+0x70]=bytes([action//256&255])*16
        self.q(0x9010,0xa000);self.mem[0xb040:0xb050]=b'F'*16
    def q(self,a,v):struct.pack_into('<Q',self.mem,a,v)
    def read(self,a,n):self.calls.append((a,n));return bytes(self.mem[a:a+n])
    def observe(self,read=None):return observe_action_binding(read or self.read,0x1000,0x76,0xb000)
    def test_newer_action_and_callback_identity(self):
        r=self.observe();self.assertEqual((r.status,r.action,r.reset_callback),('found',0x8100,0xa000))
        self.assertEqual(r.sampled_bits,b'\x81'*16)
        self.assertLessEqual(len(self.calls),512);self.assertLessEqual(sum(n for _,n in self.calls),32768)
    def test_missing_newer_falls_back_to_older_but_stop_blocks(self):
        self.q(0x7110,0)
        self.assertEqual(self.observe().action,0x8000)
        self.q(0x5120,0xc000);self.mem[0xc02c]=1
        r=self.observe();self.assertEqual((r.status,r.reason,r.sampled_bits),('fallback','stop_on_miss',b'F'*16))
    def test_bad_index_and_writer_refusal(self):
        struct.pack_into('<I',self.mem,0x1050,1)
        self.assertEqual(self.observe().reason,'selected_index_out_of_range')
        struct.pack_into('<I',self.mem,0x100c,0x100000)
        self.assertEqual(self.observe().status,'busy')
    def test_unknown_map_not_misreported_as_fallback(self):
        self.q(0x6108,0x7102)
        self.assertEqual(self.observe().status,'unsupported')
    def test_failure_each_read_and_mid_traversal_change(self):
        self.observe();n=len(self.calls)
        for fail in range(1,n+1):
            count=0
            def fault(a,n):
                nonlocal count
                count+=1
                if count==fail:raise OSError('fixture')
                return self.read(a,n)
            self.assertEqual(self.observe(fault).status,'invalid')
        headers=0
        def change(a,n):
            nonlocal headers
            if a==0x1000:
                headers+=1
                if headers==2:self.mem[0x8160]=0x99
            return self.read(a,n)
        self.assertEqual(self.observe(change).status,'unstable')
    def test_record_budget_refuses_before_array_read(self):
        struct.pack_into('<H',self.mem,0x309a,65)
        self.assertEqual(self.observe().status,'limit')
        self.assertNotIn((0x4000,8),self.calls)
    def test_pointer_change_with_identical_payload_is_unstable(self):
        self.mem[0x8060:0x8070]=self.mem[0x8160:0x8170]
        headers=0
        def change(a,n):
            nonlocal headers
            if a==0x1000:
                headers+=1
                if headers==2:self.q(0x7110,0x8000)
            return self.read(a,n)
        self.assertEqual(self.observe(change).status,'unstable')
    def test_empty_bank_fallback_and_null_storage_rejection(self):
        struct.pack_into('<H',self.mem,0x309a,0)
        self.assertEqual(self.observe().reason,'no_action')
        struct.pack_into('<H',self.mem,0x309a,1)
        self.q(0x3090,0)
        self.assertEqual(self.observe().status,'invalid')
