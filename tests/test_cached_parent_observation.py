import struct
import unittest
from engine.cached_parent_observation import capture_cached_parent


class CachedParentObservationTests(unittest.TestCase):
    def setup_memory(self):
        self.memory=bytearray(0x10000);self.base=0x100000;self.component=self.base+0x1000;self.entity=self.base+0x2000
        self.table=self.base+0x3000;self.holder=self.base+0x4000;self.bank=self.base+0x5000
        self.put(self.base,b'identity');self.put(self.component,struct.pack('<Q',self.table));self.put(self.component+0x10,struct.pack('<Q',self.entity))
        self.put(self.component+0x130,struct.pack('<8f',1,2,3,0,0,0,0,1));self.put(self.bank,struct.pack('<8f',1,2,3,1,0,0,0,1))
        self.put(self.component+0x250,struct.pack('<QQ',self.bank,self.bank))
        self.put(self.component+0x290,struct.pack('<5Q',1,0,0x1237,self.base+0x6000,self.holder))
        self.put(self.holder,struct.pack('<QII',0x100,2,0x80000000))
    def put(self,a,data):self.memory[a-self.base:a-self.base+len(data)]=data
    def read(self,plan):return [bytes(self.memory[a-self.base:a-self.base+n]) for a,n in plan]
    def capture(self,read=None):
        return capture_cached_parent(read or self.read,self.component,self.entity,self.table,
            [(self.base,b'identity')],[(self.base+0x6000,0x100,'synthetic-code')])
    def setUp(self):self.setup_memory()
    def test_reports_gate_and_pose_without_claiming_invocation(self):
        r=self.capture();self.assertTrue(r['callback_eligible']);self.assertTrue(r['banks_alias'])
        self.assertEqual(r['context_tag'],3);self.assertEqual(r['cached_parent']['position'][3],0)
        self.assertEqual(r['current_parent']['position'][3],1)
        self.assertEqual(r['supplied_code_range_matches'],['synthetic-code'])
        self.assertFalse(r['invocation_observed']);self.assertFalse(r['executable_memory_verified'])
    def test_inactive_holder_blocks_despite_nonzero_function(self):
        self.put(self.holder+12,bytes(4));r=self.capture()
        self.assertFalse(r['callback_eligible']);self.assertTrue(r['function_present'])
    def test_wrong_owner_rejected(self):
        self.put(self.component+0x10,bytes(8))
        with self.assertRaises(ValueError):self.capture()
    def test_mutations_rejected(self):
        for address,size in ((self.component+0x130,32),(self.holder,16),(self.component+0x290,40),(self.bank,32)):
            self.setup_memory();seen=[False]
            def read(plan):
                result=self.read(plan)
                if (address,size) in plan and not seen[0]:
                    seen[0]=True;self.put(address,bytes([0x77])*size)
                return result
            with self.assertRaises(ValueError):self.capture(read)
    def test_short_read_rejected(self):
        with self.assertRaises(ValueError):self.capture(lambda plan:[b'' for _ in plan])
    def test_empty_callback_and_missing_banks(self):
        self.put(self.component+0x290,bytes(40));self.put(self.component+0x250,bytes(16));r=self.capture()
        self.assertFalse(r['callback_eligible']);self.assertIsNone(r['current_parent'])
