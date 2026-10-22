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

class RadixTests(unittest.TestCase):
    def test_root_dense_and_immediate_leaf(self):
        from engine.action_map_observation import observe_action_map
        mem=bytearray(16384);base=4096
        struct.pack_into('<Q',mem,8,base+4096);mem[23]=0x23
        key=3<<56|0x1234;at=4096+3*16
        struct.pack_into('<QQ',mem,at,123,0x2c<<56|0x1234)
        read=lambda a,n:bytes(mem[a-base:a-base+n])
        r=observe_action_map(read,base|3,key)
        self.assertEqual((r.status,r.action),('found',123))
        self.assertEqual(observe_action_map(read,base|3,key+1).status,'missing')
        mem[at+15]=0x3c
        self.assertEqual(observe_action_map(read,base|3,key).status,'unsupported')
    def test_cycle_and_failed_reads(self):
        from engine.action_map_observation import observe_action_map
        # Dense node selecting itself on digit zero.
        raw=struct.pack('<QQ',4104,0x1d<<56)
        self.assertEqual(observe_action_map(lambda a,n:raw,4099,0).status,'invalid')
        self.assertEqual(observe_action_map(lambda a,n:b'',4099,0).status,'invalid')

    def test_prefix_rejection_and_path_change(self):
        from engine.action_map_observation import observe_action_map
        # Level-one dense branch compares bits 16..55 before touching children.
        raw=struct.pack('<QQ',0,0x1d<<56|0x12340000)
        self.assertEqual(observe_action_map(lambda a,n:raw,4099,0).status,'missing')
        calls=0
        def changing(a,n):
            nonlocal calls
            calls+=1
            return struct.pack('<QQ',calls,0x2c<<56|5)
        self.assertEqual(observe_action_map(changing,4099,5).status,'unstable')

    def test_depth_budget_does_not_claim_missing(self):
        from engine.action_map_observation import observe_action_map
        def chain(a,n):return struct.pack('<QQ',a+16,0x1d<<56)
        self.assertEqual(observe_action_map(chain,4099,0).status,'limit')


class ExistingLeafIntegrationTests(unittest.TestCase):
    def test_all_existing_snapshot_fixtures_through_observer(self):
        # Existing fixtures include full dense->bitmap->packed leaves, seven-byte
        # arrays and bitmap-leaf group boundaries. Use their actual byte storage.
        from tests.test_registry_snapshot import RegistrySnapshotTests
        from engine.action_map_observation import observe_action_map
        cases=[('test_dense_to_bitmap_to_inline_packed_leaf',0x1103,(1<<56)|(63<<48)|0x030201,90),
               ('test_packed_seven_byte_array_layout_boundary',0x1103,2**64-1,125),
               ('test_bitmap_leaf_uses_64_bit_groups',0x1103,0x12ff,7)]
        for method,root,key,value in cases:
            fixture=RegistrySnapshotTests(method);fixture.setUp();getattr(fixture,method)()
            result=observe_action_map(fixture.read,root,key)
            self.assertEqual((result.status,result.action),('found',value))
            self.assertEqual(int.from_bytes(fixture.read(result.value_slot,8),'little'),value)
