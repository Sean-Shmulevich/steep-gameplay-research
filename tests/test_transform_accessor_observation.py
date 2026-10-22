import json
import struct
import unittest
from engine.transform_accessor_observation import capture_transform_accessor


class TransformAccessorObservationTests(unittest.TestCase):
    def setUp(self):
        self.entity=0x101000;self.accessor=0x102000;self.mem=bytearray(0x4000)
        self.write(self.entity, '<Q', 123)
        self.write(self.entity+0x18, '<Q', self.accessor)
        self.write(self.accessor+0x40, '<Q', self.entity)
        self.write(self.accessor+0x8c, '<IIIB', 0x80100003, 9, 2, 1)
        self.plans=[]
    def write(self,a,fmt,*values):
        b=struct.pack(fmt,*values);self.mem[a-0x100000:a-0x100000+len(b)]=b
    def read(self,plan):
        self.plans.extend(plan)
        return [bytes(self.mem[a-0x100000:a-0x100000+n]) for a,n in plan]
    def capture(self,read=None):
        return capture_transform_accessor(read or self.read,self.entity,
                                          [(self.entity,struct.pack('<Q',123))])
    def test_metadata_does_not_promote_to_safe_call(self):
        result=self.capture()
        self.assertEqual(result['state']['reader_units'],3)
        self.assertEqual(result['state']['writer_units'],1)
        self.assertTrue(result['state']['high_bit'])
        self.assertFalse(result['safe_native_call_established'])
        self.assertFalse(result['lifetime_retained'])
        self.assertNotIn(str(self.accessor),json.dumps(result))
        self.assertTrue(all(n<=13 for _,n in self.plans))
    def test_inline_source_never_follows_null(self):
        self.write(self.entity+0x18,'<Q',0)
        result=self.capture()
        self.assertEqual(result['source'],'inline')
        self.assertIsNone(result['state'])
        self.assertTrue(all(a in (self.entity,self.entity+0x18) for a,_ in self.plans))
    def test_wrong_backlink_rejected(self):
        self.write(self.accessor+0x40,'<Q',self.entity+8)
        with self.assertRaisesRegex(ValueError,'backlink'):self.capture()
    def test_slot_replaced_during_read_rejected(self):
        seen=0
        def read(plan):
            nonlocal seen
            data=self.read(plan)
            if (self.accessor+0x8c,13) in plan:
                seen+=1
                if seen==1:self.write(self.entity+0x18,'<Q',0)
            return data
        with self.assertRaisesRegex(ValueError,'changed'):self.capture(read)
    def test_reader_word_changes_rejected(self):
        seen=0
        def read(plan):
            nonlocal seen
            data=self.read(plan)
            if (self.accessor+0x8c,13) in plan:
                seen+=1
                if seen==1:self.write(self.accessor+0x8c,'<I',0)
            return data
        with self.assertRaisesRegex(ValueError,'changed'):self.capture(read)
    def test_short_read_rejected(self):
        with self.assertRaisesRegex(ValueError,'incomplete'):
            self.capture(lambda plan: [b'' for _ in plan])
