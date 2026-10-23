import struct
import unittest
from engine.action_history_observation import observe_history_action


class HistoryObservationTests(unittest.TestCase):
    def setup_memory(self, selected=True):
        self.mem=bytearray(0x10000);self.calls=0
        self.action=0x1000;self.owner=0x2000;self.config=0x4000;self.table=0x5000
        for addr,value in ((self.action,self.table),(self.table+16,0x6000),
                (self.action+16,self.owner),(self.action+0xb0,self.config),
                (0x7000,0x8000),(0x8188,0x9000 if selected else 0),(0x7008,0xb000)):
            struct.pack_into('<Q',self.mem,addr,value)
        struct.pack_into('<IIIff',self.mem,self.config+0x28,0,0,1,.1,0)
        struct.pack_into('<QHH',self.mem,self.owner+0x10+0x3a0,0xc000,0x8004,1)
        struct.pack_into('<f',self.mem,0xc000,.5)
        self.clock=0xa050 if selected else 0xb008
        struct.pack_into('<Q',self.mem,self.clock,100)

    def observe(self,read):
        return observe_history_action(read,self.action,expected_table=self.table,
            expected_callback=0x6000,receiver_slot=0x7000,fallback_clock_slot=0x7008)

    def read(self,address,size):
        self.calls+=1
        return bytes(self.mem[address:address+size])

    def test_changing_values_retained_without_freshness_claim(self):
        self.setup_memory()
        def read(address,size):
            if address==self.clock:struct.pack_into('<Q',self.mem,address,100+self.calls)
            return self.read(address,size)
        result=self.observe(read)
        self.assertEqual(result['status'],'observed')
        self.assertFalse(result['dynamic_values_equal'])
        self.assertFalse(result['freshness_proven'])
        self.assertFalse(result['atomic'])
        self.assertLessEqual(result['reads'],32)
        self.assertLessEqual(result['bytes'],1024)

    def test_identity_change_and_fallback(self):
        self.setup_memory(False)
        result=self.observe(self.read)
        self.assertEqual(result['observations'][0]['identity']['clock_record'],0xb000)
        self.calls=0
        def read(address,size):
            if address==self.action and self.calls:struct.pack_into('<I',self.mem,self.config+0x2c,2)
            return self.read(address,size)
        self.assertEqual(self.observe(read)['status'],'unstable')

    def test_each_short_read_and_unsupported_channel(self):
        self.setup_memory();total=self.observe(self.read)['reads']
        for fail in range(1,total+1):
            self.setup_memory()
            def read(address,size):
                data=self.read(address,size)
                return data[:-1] if self.calls==fail else data
            self.assertEqual(self.observe(read)['status'],'invalid')
        self.setup_memory();struct.pack_into('<I',self.mem,self.config+0x28,2)
        self.assertEqual(self.observe(self.read)['status'],'unsupported')
