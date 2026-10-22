import struct
import unittest
from engine.action_ramp_observation import observe_ramp_settings

class RampObservationTests(unittest.TestCase):
    def setUp(self):
        self.mem = bytearray(65536)
        for a,v in ((0x1000,0x2000),(0x2028,0x2100),(0x3000,0x4000),
                    (0x10d0,0x5000),(0x5000,0x6000),(0x10e0,0x7000),(0x7010,0x8000)):
            struct.pack_into('<Q',self.mem,a,v)
        self.mem[0x4091]=1;self.mem[0x500f]=0x80
        struct.pack_into('<fI',self.mem,0x6028,.25,0)
        struct.pack_into('<H',self.mem,0x10f6,2)
        self.populate(2)
    def populate(self,n):
        struct.pack_into('<H',self.mem,0x701a,n)
        for i in range(n):struct.pack_into('<6fII',self.mem,0x8000+32*i,i,i,i,i,i,i,1,0)
    def read(self,a,n):return bytes(self.mem[a:a+n])
    def observe(self,read=None):return observe_ramp_settings(read or self.read,0x1000,0x2000,0x2100,0x3000)
    def test_parameters_and_maximum_budget(self):
        r=self.observe();self.assertEqual(r['status'],'observed')
        self.assertEqual(r['settings']['duration'],.25)
        self.assertEqual(r['settings']['axis_count'],2)
        self.populate(64);r=self.observe()
        self.assertEqual(r['status'],'observed');self.assertLessEqual(r['reads'],32);self.assertLessEqual(r['bytes'],4608)
        self.populate(65);self.assertEqual(self.observe()['status'],'limit')
    def test_inactive_and_global_gate_are_distinct(self):
        self.mem[0x4091]=0
        self.assertEqual(self.observe()['settings']['availability'],'active_handle')
        self.mem[0x500f]=0
        r=self.observe();self.assertEqual(r['settings']['availability'],'unresolved')
        self.assertNotIn('keys',r['settings'])
    def test_changes_and_irrelevant_bits(self):
        for significant in (True,False):
            count=0
            def read(a,n):
                nonlocal count
                if a==0x1000:
                    count+=1
                    if count==2:self.mem[0x6028 if significant else 0x500c]^=1
                return self.read(a,n)
            self.assertEqual(self.observe(read)['status'],'unstable' if significant else 'observed')
    def test_failures_at_every_read(self):
        total=self.observe()['reads']
        for fail in range(1,total+1):
            count=0
            def read(a,n):
                nonlocal count
                count+=1
                if count==fail:return b''
                return self.read(a,n)
            self.assertEqual(self.observe(read)['status'],'invalid')
    def test_refuse_unsupported_and_preserve_empty(self):
        self.populate(0);self.assertEqual(self.observe()['settings']['keys'],[])
        struct.pack_into('<f',self.mem,0x6028,0.)
        self.assertEqual(self.observe()['status'],'unsupported')
        struct.pack_into('<f',self.mem,0x6028,.25)
        struct.pack_into('<Q',self.mem,0x10e0,0)
        self.assertEqual(self.observe()['status'],'invalid')

    def test_key_mutation_and_bounds(self):
        struct.pack_into('<4f',self.mem,0x701c,0.,1.,-1.,1.)
        self.mem[0x702c]=1;self.mem[0x702d]=1
        r=self.observe()['settings']
        self.assertEqual(r['input_bounds'],(0.,1.));self.assertEqual(r['output_bounds'],(-1.,1.))
        count=0
        def read(a,n):
            nonlocal count
            if a==0x1000:
                count+=1
                if count==2:struct.pack_into('<f',self.mem,0x8004,.1)
            return self.read(a,n)
        self.assertEqual(self.observe(read)['status'],'unstable')
        struct.pack_into('<f',self.mem,0x8020,-1.)
        self.assertEqual(self.observe()['status'],'unsupported')

    def test_padding_is_not_semantic_and_signed_zero_is(self):
        for offset in (0x801c,0x8007):
            count=0
            def read(a,n):
                nonlocal count
                if a==0x1000:
                    count+=1
                    if count==2:self.mem[offset]^=0x80
                return self.read(a,n)
            self.assertEqual(self.observe(read)['status'],'observed' if offset==0x801c else 'unstable')
