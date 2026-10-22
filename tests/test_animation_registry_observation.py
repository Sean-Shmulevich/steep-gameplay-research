import json
import struct
import unittest
from engine.animation_registry_observation import capture_construction_pairs


class RegistryObservationTests(unittest.TestCase):
    def setUp(self):
        self.registry=0x101000;self.pointer=0x102000;self.mem=bytearray(0x4000);self.plans=[]
        self.write(self.registry,struct.pack('<I',123))
        self.rows([(55,66),(77,0),(55,88)])
    def write(self,address,data):self.mem[address-0x100000:address-0x100000+len(data)]=data
    def rows(self,rows):
        self.write(self.registry+0x18,struct.pack('<QI',self.pointer,8|(len(rows)<<16)))
        self.write(self.pointer,b''.join(struct.pack('<QQ',*row) for row in rows))
    def read(self,plan):
        self.plans.extend(plan)
        return [bytes(self.mem[a-0x100000:a-0x100000+n]) for a,n in plan]
    def capture(self,reader=None,**kwargs):
        return capture_construction_pairs(reader or self.read,self.registry,
            [(self.registry,struct.pack('<I',123))],**kwargs)
    def test_query_and_aliases_without_pointer_output(self):
        result=self.capture(query_identity=99)
        self.assertEqual(result['query'],dict(index=1,target_null=True,matched_key=False))
        self.assertEqual(result['pairs'][0]['key'],result['pairs'][2]['key'])
        self.assertFalse(result['safe_native_call_established'])
        self.assertNotIn(str(self.pointer),json.dumps(result))
        self.assertTrue(all(n<=256 for _,n in self.plans))
    def test_changed_rows_rejected(self):
        changed=False
        def read(plan):
            nonlocal changed
            values=self.read(plan)
            if not changed and any(a==self.pointer for a,n in plan):
                changed=True;self.write(self.pointer,struct.pack('<Q',999))
            return values
        with self.assertRaisesRegex(ValueError,'contents changed'):self.capture(read)
    def test_changed_header_rejected(self):
        def read(plan):
            values=self.read(plan)
            if any(a==self.pointer for a,n in plan):self.write(self.registry+0x22,struct.pack('<H',2))
            return values
        with self.assertRaisesRegex(ValueError,'header changed'):self.capture(read)
    def test_budget_rejects_before_payload_read(self):
        with self.assertRaisesRegex(ValueError,'budget'):self.capture(max_pairs=2)
        self.assertFalse(any(a==self.pointer for a,n in self.plans))
    def test_empty_null_storage_is_not_followed(self):
        self.write(self.registry+0x18,bytes(12));result=self.capture()
        self.assertEqual(result['pairs'],[])
        self.assertFalse(any(a==0 for a,n in self.plans))
    def test_short_read_rejected(self):
        with self.assertRaisesRegex(ValueError,'incomplete'):self.capture(lambda plan:[b'' for _ in plan])
    def test_invalid_capacity_rejected(self):
        self.write(self.registry+0x20,struct.pack('<I',2|(3<<16)))
        with self.assertRaisesRegex(ValueError,'capacity'):self.capture()

    def test_public_demo_exercises_null_row_precedence(self):
        from engine.examples.animation_registry_observation_demo import run
        result=run()
        self.assertFalse(result['game_process'])
        self.assertEqual(result['observation']['query'],
                         dict(index=1,target_null=True,matched_key=False))
        self.assertEqual(result['observation']['count'],3)
