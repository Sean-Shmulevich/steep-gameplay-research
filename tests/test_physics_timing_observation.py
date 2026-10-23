import struct
import unittest
from engine.physics_timing_observation import observe_physics_timing

class TimingObservationTests(unittest.TestCase):
    def fixture(self, count=2, capacity=3):
        owner,manager,policy,history,world=0x10000,0x20000,0x30000,0x40000,0x50000
        raw=bytearray(52)
        struct.pack_into('<4f',raw,0,0,.02,50,100)
        struct.pack_into('<Q5If',raw,16,history,count,count%capacity if capacity else 0,0,capacity,2,.01)
        raw[48]=1
        payload=struct.pack('<3I',0x3c23d70a,0x3cf5c28f,0x7fc01234)[:capacity*4]
        memory={owner:struct.pack('<Q',manager),owner+0x1368:bytes(raw),policy:b'\0',history:payload,
                manager+8:struct.pack('<Q',world),world+0x1060:struct.pack('<f',.03)}
        return (owner,manager,policy),memory

    def test_two_samples_with_unused_nan_and_history_order(self):
        args,memory=self.fixture()
        result=observe_physics_timing(lambda a,n:memory[a],*args)
        self.assertEqual(result['status'],'observed')
        self.assertEqual(result['reads'],12)
        self.assertEqual(result['timing']['history_count'],2)
        self.assertEqual(result['timing']['chronological_history_bits'],[0x3c23d70a,0x3cf5c28f])
        self.assertFalse(result['producer_input_proved'])
        self.assertFalse(result['atomic_snapshot'])

    def test_each_short_read_refused(self):
        for fail in range(12):
            args,memory=self.fixture();calls=[]
            def read(a,n):
                calls.append(a)
                return b'' if len(calls)==fail+1 else memory[a]
            result=observe_physics_timing(read,*args)
            self.assertEqual(result['status'],'short_read')
            self.assertNotIn('timing',result)

    def test_policy_change_and_owner_change(self):
        args,memory=self.fixture();calls=[]
        def read(a,n):
            calls.append(a)
            return b'\1' if a==args[2] and len(calls)>6 else memory[a]
        self.assertEqual(observe_physics_timing(read,*args)['status'],'unstable')
        memory[args[0]]=struct.pack('<Q',999)
        self.assertEqual(observe_physics_timing(lambda a,n:memory[a],*args)['status'],'owner_changed')

    def test_ring_limit_prevents_payload_read(self):
        args,memory=self.fixture();raw=bytearray(memory[args[0]+0x1368]);struct.pack_into('<I',raw,36,65)
        memory[args[0]+0x1368]=bytes(raw)
        result=observe_physics_timing(lambda a,n:memory[a],*args)
        self.assertEqual(result['status'],'limit')
        self.assertEqual(result['reads'],3)

    def test_initialized_zero_steps_is_not_rejected(self):
        args,memory=self.fixture(count=0,capacity=0)
        raw=bytearray(memory[args[0]+0x1368]);struct.pack_into('<I',raw,40,0)
        memory[args[0]+0x1368]=bytes(raw)
        result=observe_physics_timing(lambda a,n:memory[a],*args)
        self.assertEqual(result['status'],'observed')
        self.assertEqual(result['timing']['step_count'],0)
        self.assertGreater(result['timing']['elapsed'],0)

    def test_wrapped_history_and_invalid_live_lane(self):
        args,memory=self.fixture(count=3)
        raw=bytearray(memory[args[0]+0x1368]);struct.pack_into('<II',raw,28,1,1)
        memory[args[0]+0x1368]=bytes(raw)
        memory[0x40000]=struct.pack('<3f',.01,.02,.03)
        result=observe_physics_timing(lambda a,n:memory[a],*args)
        self.assertEqual(result['status'],'observed')
        expected=list(struct.unpack('<3I',struct.pack('<3f',.02,.03,.01)))
        self.assertEqual(result['timing']['chronological_history_bits'],expected)
        memory[0x40000]=struct.pack('<3f',float('nan'),.02,.03)
        self.assertEqual(observe_physics_timing(lambda a,n:memory[a],*args)['status'],'unsupported_values')
