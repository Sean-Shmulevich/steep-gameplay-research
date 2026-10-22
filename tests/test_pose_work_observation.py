import struct
import unittest
from engine.pose_work_observation import capture_pose_work_packet
from engine.pose_work_observation import capture_pose_work_boundary


class PoseWorkObservationTests(unittest.TestCase):
    def setUp(self):
        self.base=0x100000;self.memory=bytearray(0x10000)
        self.component=self.base+0x1000;self.entity=self.base+0x2000;self.table=self.base+0x3000
        self.packet=self.base+0x4000;self.inp=self.base+0x5000;self.out=self.base+0x6000;self.bank=self.base+0x7000
        self.put(self.base,b'identity');self.put(self.component,struct.pack('<Q',self.table))
        self.put(self.component+16,struct.pack('<Q',self.entity));self.put(self.component+0x258,struct.pack('<Q',self.bank))
        self.put(self.packet,struct.pack('<QQf',self.inp,self.out,.016))
        for address,primary in ((self.inp,self.bank),(self.out,0)):
            self.put(address,struct.pack('<4QI',self.component,primary,0,address+0x24,32772))
            self.put(address+0x300,struct.pack('<HB',65535,0xa8))
    def put(self,address,value):self.memory[address-self.base:address-self.base+len(value)]=value
    def read(self,plan):return [bytes(self.memory[a-self.base:a-self.base+n]) for a,n in plan]
    def capture(self,reader=None):
        return capture_pose_work_packet(reader or self.read,self.packet,self.component,self.entity,self.table,[(self.base,b'identity')])
    def test_initialized_pattern_without_execution_claim(self):
        result=self.capture()
        self.assertTrue(result['initialization_pattern_matches'])
        self.assertTrue(result['input']['primary_matches_current'])
        self.assertEqual(result['output']['flags'],0xa8)
        self.assertFalse(result['callback_execution_verified'])
        self.assertFalse(result['lifetime_pinned'])
    def test_boundary_uses_caller_stack_and_filters_without_reads(self):
        reads=[]
        def read(plan):reads.extend(plan);return self.read(plan)
        args=(self.component,self.entity,self.table,[(self.base,b'identity')])
        self.assertIsNone(capture_pose_work_boundary(read,
            dict(rdi=self.component+8,rsp=self.packet-48),*args))
        self.assertEqual(reads,[])
        result=capture_pose_work_boundary(read,
            dict(rdi=self.component,rsp=self.packet-48),*args)
        self.assertTrue(result['initialization_pattern_matches'])
        self.assertIn((self.packet,20),reads)
    def test_boundary_rejects_missing_registers(self):
        with self.assertRaises(ValueError):
            capture_pose_work_boundary(self.read,dict(rdi=self.component),
                self.component,self.entity,self.table,[(self.base,b'identity')])
    def test_populated_output_is_observation_not_initialization(self):
        self.put(self.out+8,struct.pack('<Q',self.bank))
        result=self.capture()
        self.assertFalse(result['initialization_pattern_matches'])
        self.assertTrue(result['output']['primary_matches_current'])
    def test_wrong_component_or_owner_refused(self):
        for address in (self.component+16,self.inp,self.out):
            self.setUp();self.put(address,bytes(8))
            with self.assertRaises(ValueError):self.capture()
    def test_changed_packet_wrapper_and_external_guard_refused(self):
        for address,size in ((self.packet,20),(self.inp,36),(self.out+0x300,3),(self.base,8)):
            self.setUp();changed=[False]
            def read(plan):
                values=self.read(plan)
                if (address,size) in plan and not changed[0]:
                    changed[0]=True;self.put(address,bytes([0x55])*size)
                return values
            with self.assertRaises(ValueError):self.capture(read)
    def test_incomplete_nonfinite_and_alias_refused(self):
        with self.assertRaises(ValueError):self.capture(lambda p:[b'' for _ in p])
        self.put(self.packet+16,struct.pack('<f',float('nan')))
        with self.assertRaises(ValueError):self.capture()
        self.setUp();self.put(self.packet+8,struct.pack('<Q',self.inp))
        with self.assertRaises(ValueError):self.capture()
