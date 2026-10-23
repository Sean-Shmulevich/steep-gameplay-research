import struct
import unittest
from engine.timing_service_observation import observe_timing_service


class ServiceObservationTests(unittest.TestCase):
    def fixture(self, count=1):
        memory = {}
        def put(address, fmt, *values):
            for i, b in enumerate(struct.pack(fmt, *values)):
                memory[address+i] = b
        args = dict(singleton_address=0x100, registry_address=0x108,
                    expected_vtable=0x2000, expected_dispatch=0x3000,
                    expected_world=0x4000, expected_manager=0x6000, expected_owner=0x7000)
        put(0x100, '<QQ', 0x1000, 0x8000)
        put(0x1000, '<Q', 0x2000); put(0x2048, '<Q', 0x3000)
        put(0x8072, '<QHH', 0x9000, 0, count)
        for i in range(count):
            put(0x9000+8*i, '<Q', 0xa000+16*i)
            put(0xa000+16*i, '<QIi', 0x4000 if i==0 else 0xb000+i*32, 0, -1)
        put(0x4ff0, '<Q', 0x6000); put(0x6018, '<Q', 0x7000); put(0x7000, '<Q', 0x6000)
        def read(address, size):
            return bytes(memory[address+i] for i in range(size))
        return args, read, put

    def test_maximum_and_empty(self):
        args, read, _ = self.fixture(32)
        r=observe_timing_service(read, **args)
        self.assertEqual(r['status'], 'qualified')
        self.assertLessEqual(r['reads'],84);self.assertLessEqual(r['bytes'],2048)
        self.assertFalse(r['dispatch_execution_proved'])
        args, read, _=self.fixture(0)
        self.assertEqual(observe_timing_service(read,**args)['status'],'world_absent')

    def test_every_short_read_refuses_without_binding(self):
        args, read, _=self.fixture()
        n=observe_timing_service(read,**args)['reads']
        for failure in range(n):
            calls=0
            def faulty(address,size):
                nonlocal calls
                calls+=1
                return b'' if calls-1==failure else read(address,size)
            result=observe_timing_service(faulty,**args)
            self.assertEqual(result['status'],'short_read');self.assertNotIn('binding',result)

    def test_type_dispatch_membership_and_owner_guards(self):
        for address,fmt,value,status in [
            (0x1000,'<Q',1,'wrong_service_type'),(0x2048,'<Q',1,'dispatch_changed'),
            (0xa00c,'<i',0,'world_absent'),(0x4ff0,'<Q',1,'manager_changed'),
            (0x7000,'<Q',1,'owner_changed'),(0x807c,'<H',33,'limit')]:
            args,read,put=self.fixture();put(address,fmt,value)
            self.assertEqual(observe_timing_service(read,**args)['status'],status)

    def test_changed_identity_and_duplicate_membership(self):
        args,read,put=self.fixture();seen=0
        def changing(address,size):
            nonlocal seen
            if address==0x100:
                seen+=1
                if seen==2:
                    put(0x100,'<Q',0x1100);put(0x1100,'<Q',0x2000)
            return read(address,size)
        self.assertEqual(observe_timing_service(changing,**args)['status'],'unstable')
        args,read,put=self.fixture(2);put(0xa010,'<Q',0x4000)
        self.assertEqual(observe_timing_service(read,**args)['status'],'world_membership_ambiguous')
