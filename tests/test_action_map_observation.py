import struct
import unittest
from engine.action_map_observation import observe_compact_map

class MapTests(unittest.TestCase):
    def fixture(self,count=3):
        memory=bytearray(1024);struct.pack_into('<Q',memory,0,count-1)
        keys=[10+i*2 for i in range(count)]
        struct.pack_into('<'+'Q'*count,memory,8,*keys)
        area=next(n for n in (2,3,4,6,8,12,16,24,32) if n>=count+1)
        for i in range(count):struct.pack_into('<Q',memory,(area+i)*8,100+i)
        calls=[]
        def read(a,n):calls.append((a,n));return bytes(memory[a-4096:a-4096+n])
        return memory,keys,read,calls
    def test_every_supported_size_hit_miss_and_bounds(self):
        for count in range(1,32):
            _,keys,read,calls=self.fixture(count)
            r=observe_compact_map(read,4097,keys[-1]);self.assertEqual((r.status,r.action,r.count),('found',99+count,count))
            self.assertEqual(len(calls),6);self.assertLessEqual(sum(n for _,n in calls),528)
            self.assertEqual(observe_compact_map(read,4097,keys[-1]+1).status,'missing')
    def test_null_and_unsupported_are_distinct(self):
        def read(*args):self.fail('should not read')
        self.assertEqual(observe_compact_map(read,0,2).status,'missing')
        self.assertEqual(observe_compact_map(read,4099,2).status,'unsupported')
    def test_fault_each_read(self):
        for fail in range(1,7):
            _,keys,read,_=self.fixture();calls=0
            def fault(a,n):
                nonlocal calls
                calls+=1
                if calls==fail:raise OSError('fixture')
                return read(a,n)
            self.assertEqual(observe_compact_map(fault,4097,keys[0]).status,'invalid')
    def test_unstable_value_unsorted_and_null_value(self):
        memory,keys,read,calls=self.fixture()
        def changed(a,n):
            if len(calls)==3:struct.pack_into('<Q',memory,32,777)
            return read(a,n)
        self.assertEqual(observe_compact_map(changed,4097,keys[0]).status,'unstable')
        struct.pack_into('<Q',memory,32,0)
        r=observe_compact_map(read,4097,keys[0]);self.assertEqual((r.status,r.action),('found',0))
        struct.pack_into('<Q',memory,16,9)
        self.assertEqual(observe_compact_map(read,4097,keys[0]).status,'invalid')
