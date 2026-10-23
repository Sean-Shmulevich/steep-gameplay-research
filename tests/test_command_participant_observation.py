import struct
import unittest
from engine.command_participant_observation import observe_command_participants

class ParticipantObservationTests(unittest.TestCase):
    def fixture(self,count=2):
        mem={}
        def put(a,fmt,*v):
            for i,b in enumerate(struct.pack(fmt,*v)):mem[a+i]=b
        put(0x1100,'<Q',0x5000);put(0x50b0,'<QHH',0x6000,32,count)
        for i in range(count):
            put(0x6000+i*8,'<Q',0x7000+i*16);put(0x7000+i*16,'<Q',0x1800)
        put(0x1800,'<QQ',0x2000,0x2100)
        def read(a,n):return bytes(mem[a+i] for i in range(n))
        return dict(singleton_address=0x1100,image_range=(0x1000,0x4000),code_range=(0x2000,0x3000)),read,put

    def test_max_list_empty_and_shared_table(self):
        for n in (0,2,32):
            args,read,_=self.fixture(n);r=observe_command_participants(read,**args)
            self.assertEqual(r['status'],'observed');self.assertEqual(r['registry']['count'],n)
            self.assertLessEqual(r['reads'],134);self.assertLessEqual(r['bytes'],2100)
            self.assertFalse(r['execution_proved'])

    def test_short_read_at_every_point(self):
        args,read,_=self.fixture();count=observe_command_participants(read,**args)['reads']
        for fail in range(count):
            calls=0
            def faulty(a,n):
                nonlocal calls
                calls+=1
                return b'' if calls==fail+1 else read(a,n)
            r=observe_command_participants(faulty,**args)
            self.assertEqual(r['status'],'short_read');self.assertNotIn('registry',r)

    def test_bounds_and_method_changes(self):
        for a,fmt,value,status in [(0x1100,'<Q',0,'manager_unavailable'),(0x50ba,'<H',33,'limit'),(0x7000,'<Q',0x9000,'table_outside_image'),(0x1800,'<Q',0x1100,'method_outside_code')]:
            args,read,put=self.fixture();put(a,fmt,value)
            self.assertEqual(observe_command_participants(read,**args)['status'],status)
        args,read,put=self.fixture();calls=0
        def changed(a,n):
            nonlocal calls
            if a==0x1100:
                calls+=1
                if calls==2:put(0x1800,'<Q',0x2200)
            return read(a,n)
        self.assertEqual(observe_command_participants(changed,**args)['status'],'unstable')
