import struct
import unittest
from engine.markup_listener_observation import observe_markup_listeners

class MarkupListenerTests(unittest.TestCase):
    def fixture(self):
        base=0x10000;memory=bytearray(0x10000);calls=[]
        def put(at,fmt,*values):struct.pack_into(fmt,memory,at-base,*values)
        memory[:8]=b'identity'
        dispatcher=0x10100;records=0x11000;root=0x13000;vector=0x14000;array=0x15000
        put(dispatcher+0x50,'<Q',records);put(dispatcher+0x5a,'<H',148);put(dispatcher+0x60,'<Q',root|1)
        put(records+92*20+8,'<i',-1);put(records+92*20+16,'<i',1)
        put(root,'<QQQ',0,92,vector);put(vector+8,'<QHH',array,2,2)
        put(array,'<5Q',0x18000,0x19000,0,0x16002,0x19100)
        put(array+40,'<5Q',0x18000,0,0,0,0x19100)
        def read(at,n):
            calls.append((at,n))
            if not base<=at<=base+len(memory)-n:raise OSError('unmapped')
            return bytes(memory[at-base:at-base+n])
        return memory,put,read,calls,dispatcher,[(base,b'identity')]

    def test_copied_descriptors_and_dispatch_presence(self):
        _,_,read,_,d,g=self.fixture();r=observe_markup_listeners(read,d,92,g)
        self.assertEqual(r['status'],'found');self.assertEqual(r['link_count'],1)
        self.assertEqual(r['entries'][0]['receiver'],0x16000)
        self.assertEqual(r['entries'][0]['receiver_tags'],2)
        self.assertTrue(r['entries'][0]['callable_in_dispatch'])
        self.assertFalse(r['entries'][1]['callable_in_dispatch'])
        self.assertFalse(r['callback_execution_proved'])
        self.assertFalse(r['atomic_snapshot'])

    def test_missing_null_unsupported_empty_and_budget(self):
        for root,status in [(0,'missing'),(0x13002,'unsupported')]:
            _,put,read,_,d,g=self.fixture();put(d+0x60,'<Q',root)
            self.assertEqual(observe_markup_listeners(read,d,92,g)['status'],status)
        _,put,read,_,d,g=self.fixture();put(0x13010,'<Q',0)
        self.assertEqual(observe_markup_listeners(read,d,92,g)['status'],'present_null')
        _,put,read,_,d,g=self.fixture();put(0x14012,'<H',0);put(0x14008,'<Q',0)
        self.assertEqual(observe_markup_listeners(read,d,92,g)['entries'],[])
        _,put,read,_,d,g=self.fixture();put(0x14012,'<H',129)
        with self.assertRaises(ValueError):observe_markup_listeners(read,d,92,g)

    def test_faults_never_report_success(self):
        _,_,read,calls,d,g=self.fixture();observe_markup_listeners(read,d,92,g)
        for failure in range(len(calls)):
            _,_,read,_,d,g=self.fixture();n=0
            def fault(a,size):
                nonlocal n
                n+=1
                if n==failure+1:raise OSError('fixture')
                return read(a,size)
            try:r=observe_markup_listeners(fault,d,92,g)
            except (ValueError,OSError):continue
            self.assertNotEqual(r['status'],'found')

    def test_changed_descriptors_header_and_guards_rejected(self):
        for target in (0x15000,0x10150,0x10000):
            _,_,read,_,d,g=self.fixture();hits=0
            def changed(a,n):
                nonlocal hits
                b=read(a,n)
                if a==target:
                    hits+=1
                    if hits==2:b=bytes([b[0]^1])+b[1:]
                return b
            with self.assertRaises(ValueError):observe_markup_listeners(changed,d,92,g)
