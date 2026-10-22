import json
import struct
import unittest
from engine.player_animation_observation import capture_player_animation


class PlayerAnimationObservationTests(unittest.TestCase):
    def setUp(self):
        self.base=0x100000;self.entity=self.base+0x1000;self.component=self.base+0x4000
        self.memory=bytearray(0x20000);self.requests=[]
        self.profile=dict(entity_tables=[0x200],skeleton_table=0x300,type_getter=0x500,descriptor_global=0x600)
        self.put(self.entity,'<Q',self.base+0x200)
        self.put(self.entity+0x88,'<QHH',self.base+0x3000,0,1)
        self.put(self.base+0x3000,'<Q',self.component)
        self.put(self.entity+0x1aa,'<BBH',7,0,0);self.put(self.entity+0x1f9,'<B',7)
        self.put(self.component,'<Q',self.base+0x300);self.put(self.component+0x10,'<Q',self.entity)
        self.put(self.base+0x330,'<Q',self.base+0x500)
        self.write(self.base+0x500,b'\x48\x8b\x05'+struct.pack('<i',0xf9)+b'\xc3')
        self.put(self.base+0x600,'<Q',self.base+0x8000)
        self.put(self.base+0x8018,'<Q',self.base+0x9000);self.put(self.base+0x804c,'<HH',12,19)
        self.write(self.base+0x9000,b'SkeletonComponent\0')
        self.put(self.component+0x240,'<Q',self.base+0xb000)
        self.put(self.base+0xb038,'<QHH',self.base+0xc000,0,1)
        self.put(self.base+0xc000,'<II',10,0)
        self.put(self.component+0x258,'<4Q',self.base+0xd000,0,self.base+0xd000,0)
        self.put(self.base+0xd000,'<8f',10,20,30,0,0,0,0,1)
        self.put(self.base+0xd190,'<Q',self.base+0xe000)
        self.put(self.base+0xe014,'<HH',32,32);self.put(self.base+0xe05a,'<H',1)
        self.put(self.base+0xd198,'<Q',self.base+0xf000)
        self.put(self.base+0xf000,'<8f',1,2,3,0,0,0,0,1)
        self.guard=(self.base+0xa000,b'identity');self.write(*self.guard)
    def write(self,address,value):self.memory[address-self.base:address-self.base+len(value)]=value
    def put(self,address,fmt,*values):self.write(address,struct.pack(fmt,*values))
    def read(self,plan):
        self.requests.extend(plan)
        return [bytes(self.memory[a-self.base:a-self.base+n]) for a,n in plan]
    def capture(self,read=None):
        return capture_player_animation(read or self.read,self.entity,self.base,[10,99],[self.guard],self.profile)
    def test_composed_observation_and_limits(self):
        result=self.capture()
        self.assertTrue(result['pose']['channels'][0]['found'])
        self.assertFalse(result['pose']['channels'][1]['found'])
        self.assertEqual(result['pose']['record_count_source'],'native_metadata')
        self.assertTrue(result['pose']['selection_boundary']['endpoints_matched'])
        self.assertFalse(result['suitable_for_animation_writes'])
        self.assertFalse(result['atomic_snapshot']);self.assertFalse(result['lifetime_pinned'])
        self.assertNotIn(str(self.component),json.dumps(result))
    def test_owner_mismatch_rejected_before_pose_data(self):
        self.put(self.component+0x10,'<Q',self.entity+8)
        with self.assertRaises(ValueError):self.capture()
        self.assertNotIn((self.base+0xf000,32),self.requests)
    def test_source_slot_change_during_pose_read_rejected(self):
        def changing(plan):
            result=self.read(plan)
            if (self.base+0xf000,32) in plan:self.put(self.base+0x3000,'<Q',self.component+0x100)
            return result
        with self.assertRaises(ValueError):self.capture(changing)
    def test_epoch_change_rejected(self):
        def changing(plan):
            result=self.read(plan)
            if (self.base+0xf000,32) in plan:self.put(self.component+0xc58,'<I',1)
            return result
        with self.assertRaisesRegex(ValueError,'epoch'):self.capture(changing)
    def test_incomplete_transport_rejected(self):
        with self.assertRaises(ValueError):self.capture(lambda plan:[])
