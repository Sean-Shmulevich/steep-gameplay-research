import json
import struct
import unittest
from engine.animation_event_observation import capture_event_queue


class EventQueueObservationTests(unittest.TestCase):
    def setUp(self):
        self.base, self.component, self.owner = 0x140000000, 0x100000, 0x200000
        self.queue = self.component+0xf0
        self.memory = {}
        self.calls = []
        self.put(0x90000, b'identity')
        self.put(self.component, struct.pack('<Q', self.base+0x1f289d0))
        self.put(self.component+16, struct.pack('<Q', self.owner))
        self.header(1)
        for array, pointer in [(0x300000,0x400000),(0x310000,0x500000),(0x320000,0x510000)]:
            self.put(array, struct.pack('<Q', pointer))
        self.put(0x400000, struct.pack('<Q', self.base+0x1eecd58))
        self.put(self.base+0x1eecd58+0x50, struct.pack('<Q', self.base+0xa45ec0))
        for h in (0x500000,0x510000):
            self.put(h, struct.pack('<QII', self.owner, 7, 0x80000001))

    def put(self, address, data):
        self.memory.update({address+i: b for i,b in enumerate(data)})

    def header(self, count, second=None):
        for offset, address, n in [(0,0x300000,count),(0x90,0x310000,count),
                                    (0x120,0x320000,count if second is None else second)]:
            self.put(self.queue+offset, struct.pack('<QHH',address,0x8010,n))

    def read(self, plan):
        self.calls.append(plan)
        return [bytes(self.memory[a+i] for i in range(n)) for a,n in plan]

    def capture(self, reader=None):
        return capture_event_queue(reader or self.read,self.component,self.owner,
                                   self.base,0x4000000,[(0x90000,b'identity')])

    def test_classification_aliases_and_no_heap_addresses(self):
        result=self.capture(); row=result['rows'][0]
        self.assertEqual(row['type_name'],'AudioEventSeed')
        self.assertEqual(row['handler_rva'],0xa45ec0)
        self.assertEqual(row['first']['alias'],row['second']['alias'])
        self.assertTrue(row['first']['matches_owner'])
        self.assertFalse(result['callback_execution_established'])
        self.assertNotIn(str(self.owner),json.dumps(result))
        self.assertTrue(all(len(p)<=32 for p in self.calls))

    def test_inactive_handle_does_not_resolve_stale_pointer(self):
        self.put(0x500000+12,struct.pack('<I',1))
        row=self.capture()['rows'][0]
        self.assertFalse(row['first']['nonnull'])
        self.assertIsNone(row['first']['alias'])
        self.assertFalse(row['first']['matches_owner'])

    def test_empty_queue_and_null_event_skip_dereferences(self):
        self.header(0)
        self.assertEqual(self.capture()['rows'],[])
        self.header(1)
        self.put(0x300000,bytes(8))
        self.put(0x310000,bytes(8));self.put(0x320000,bytes(8))
        self.assertEqual(self.capture()['rows'],[dict(index=0,event_present=False)])

    def test_foreign_table_not_dereferenced(self):
        self.put(0x400000,struct.pack('<Q',0xdead0000))
        row=self.capture()['rows'][0]
        self.assertFalse(row['table_in_image'])
        self.assertEqual(row['type_name'],'unknown')
        self.assertIsNone(row['handler_rva'])

    def test_mismatched_counts_and_oversize_rejected(self):
        self.header(1,second=0)
        with self.assertRaisesRegex(ValueError,'counts disagree'):self.capture()
        self.header(65)
        with self.assertRaisesRegex(ValueError,'oversized'):self.capture()

    def test_changes_to_queue_handle_owner_and_callback_rejected(self):
        for address in (self.queue,0x500000+12,self.component+16,self.base+0x1eecd58+0x50):
            with self.subTest(address=address):
                self.setUp();seen=0
                def reader(plan):
                    nonlocal seen
                    blocks=self.read(plan)
                    for i,(a,n) in enumerate(plan):
                        if a==address:
                            seen+=1
                            if seen==2:blocks[i]=bytes([blocks[i][0]^1])+blocks[i][1:]
                    return blocks
                with self.assertRaisesRegex(ValueError,'changed'):self.capture(reader)

    def test_reference_count_changes_do_not_invalidate_resolution(self):
        def reader(plan):
            self.put(0x500000+8,struct.pack('<I',123))
            return self.read(plan)
        self.assertTrue(self.capture(reader)['guards_matched'])

    def test_wrong_owner_table_and_incomplete_transport(self):
        self.put(self.component+16,struct.pack('<Q',0x600000))
        with self.assertRaisesRegex(ValueError,'owner mismatch'):self.capture()
        self.setUp();self.put(self.component,struct.pack('<Q',self.base+1))
        with self.assertRaisesRegex(ValueError,'component table'):self.capture()
        with self.assertRaisesRegex(ValueError,'incomplete'):self.capture(lambda plan:[])

    def test_maximum_queue_stays_batched_and_preserves_order(self):
        for offset,array,pointer in [(0,0x300000,0x400000),(0x90,0x310000,0x500000),(0x120,0x320000,0x510000)]:
            self.put(self.queue+offset,struct.pack('<QHH',array,0x8040,64))
            self.put(array,struct.pack('<64Q',*([pointer]*64)))
        result=self.capture()
        self.assertEqual([r['index'] for r in result['rows']],list(range(64)))
        self.assertLessEqual(len(self.calls),32)
        self.assertTrue(all(len(plan)<=32 for plan in self.calls))

    def test_foreign_handler_is_not_presented_as_image_rva(self):
        self.put(self.base+0x1eecd58+0x50,struct.pack('<Q',0x777000))
        row=self.capture()['rows'][0]
        self.assertEqual(row['type_name'],'AudioEventSeed')
        self.assertFalse(row['handler_in_image'])
        self.assertIsNone(row['handler_rva'])
