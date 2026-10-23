import struct
import unittest
from engine.motion_membership_observation import capture_motion_membership, scan_registry


class MotionMembershipObservationTests(unittest.TestCase):
    def setUp(self):
        self.base = 0x140000000
        self.entity, self.world, self.graph = 0x100000, 0x200000, 0x300000
        self.source, self.storage, self.other = 0x400000, 0x500000, 0x700000
        self.ptable, self.otable = self.base + 0x1f00000, self.base + 0x1f10000
        q = lambda v: struct.pack('<Q', v)
        self.mem = {0x90000: b'identity', self.entity + 0x60: q(self.world),
            self.world + 0x1038: q(self.graph), self.graph: q(self.world),
            self.graph + 0x4ad8: q(self.base + 0x1ec7f38),
            self.graph + 0x4c98: q(self.base + 0x8b9750),
            self.world + 0x730: struct.pack('<QiI', self.source, 2, 2 | 0x80000000),
            self.graph + 0x4c70: struct.pack('<Qii', self.storage, 0, 3),
            self.source: struct.pack('<2Q', self.other, self.entity),
            self.storage: struct.pack('<3Q', self.other, self.entity, 0xdead),
            self.entity: q(self.ptable) + bytes(8) + q(0),
            self.other: q(self.otable) + bytes(8) + q(0x800000),
            self.ptable + 0x270: q(self.base + 0x900000),
            self.otable + 0x270: q(self.base + 0x910000)}

    def reader(self, plan):
        result = []
        for address, size in plan:
            if address not in self.mem:
                self.fail('Unexpected dereference: ' + hex(address))
            result.append(self.mem[address][:size])
        return result

    def capture(self, read=None):
        return capture_motion_membership(read or self.reader, self.entity, self.world,
                                         self.base, [(0x90000, b'identity')])

    def test_entity_receiver_reported_with_table_and_method(self):
        r = self.capture()
        self.assertTrue(r['source_membership_observed'])
        self.assertEqual(r['entity_source_indices'], [1])
        self.assertEqual(r['entity_table_rva'], 0x1f00000)
        self.assertEqual(r['entity_motion_method_rva'], 0x900000)
        row = r['receivers'][1]
        self.assertEqual((row['is_entity'], row['table_rva'], row['motion_method_rva']),
                         (True, 0x1f00000, 0x900000))
        self.assertEqual(row['storage_indices'], [1])
        self.assertEqual(row['unclaimed_prefix_indices'], [])
        self.assertEqual(r['receivers'][0]['motion_method_rva'], 0x910000)
        for flag in ('callback_execution_established', 'input_freshness_established',
                     'safe_to_step_established', 'atomic_snapshot'):
            self.assertFalse(r[flag])

    def test_unclaimed_prefix_reported_separately(self):
        self.mem[self.graph + 0x4c70] = struct.pack('<Qii', self.storage, 2, 3)
        self.assertEqual(self.capture()['receivers'][1]['unclaimed_prefix_indices'], [1])

    def test_absent_entity_is_not_membership(self):
        self.mem[self.source] = struct.pack('<2Q', self.other, self.other)
        r = self.capture()
        self.assertFalse(r['source_membership_observed'])
        self.assertEqual(r['entity_source_indices'], [])

    def test_empty_source_does_not_dereference_old_storage(self):
        self.mem[self.world + 0x730] = struct.pack('<QiI', 0, 0, 0)
        r = self.capture()
        self.assertEqual((r['source_count'], r['storage_capacity'], r['receivers']), (0, 3, []))

    def test_table_outside_image_is_not_followed(self):
        self.mem[self.other] = struct.pack('<QQQ', 0x123456000, 0, 0x800000)
        row = self.capture()['receivers'][0]
        self.assertEqual((row['table_rva'], row['motion_method_rva']), (None, None))

    def test_job_identity_checks(self):
        for address, message in ((self.graph + 0x4ad8, 'job table'),
                                 (self.graph + 0x4c98, 'callback'),
                                 (self.graph, 'backlink'),
                                 (self.entity + 0x60, 'different world')):
            saved = self.mem[address]
            self.mem[address] = struct.pack('<Q', 0xdead0000)
            with self.assertRaisesRegex(ValueError, message):
                self.capture()
            self.mem[address] = saved

    def test_invalid_headers_rejected(self):
        for remaining, capacity in ((-1, 3), (4, 3), (0, 1025)):
            self.mem[self.graph + 0x4c70] = struct.pack('<Qii', self.storage, remaining, capacity)
            with self.assertRaisesRegex(ValueError, 'storage'):
                self.capture()
        self.mem[self.graph + 0x4c70] = struct.pack('<Qii', self.storage, 0, 3)
        self.mem[self.world + 0x730] = struct.pack('<QiI', self.source, 300, 400)
        with self.assertRaisesRegex(ValueError, 'source'):
            self.capture()

    def test_changed_source_rejected(self):
        reads = 0
        def reader(plan):
            nonlocal reads
            result = self.reader(plan)
            for i, (a, _) in enumerate(plan):
                if a == self.source:
                    reads += 1
                    if reads == 2:
                        result[i] = bytes(16)
            return result
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.capture(reader)

    def test_short_transport_rejected(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.capture(lambda plan: [])

    def test_ai_preupdate_batch_and_unknown_batch(self):
        q = lambda v: struct.pack('<Q', v)
        self.mem.update({self.graph + 0x1ae0: q(self.base + 0x1ec7f38),
                         self.graph + 0x1ca0: q(self.base + 0x8b9750),
                         self.world + 0x270: struct.pack('<QiI', self.source, 2, 2),
                         self.graph + 0x1c78: struct.pack('<Qii', self.storage, 1, 3)})
        r = capture_motion_membership(self.reader, self.entity, self.world, self.base,
                                      [(0x90000, b'identity')], job=0x1ae0, entry=0x270)
        self.assertEqual((r['batch'], r['registry_entry'], r['entity_source_indices']),
                         ('Ai::UpdateAIPreUpdate', 5, [1]))
        with self.assertRaisesRegex(ValueError, 'unrecognised'):
            capture_motion_membership(self.reader, self.entity, self.world, self.base,
                                      [(0x90000, b'identity')], job=0x1234, entry=0x270)

    def test_registry_scan_reports_entity_entries(self):
        hdr = lambda i: self.world + 0x130 + i * 0x40
        for i in range(8):
            self.mem[hdr(i)] = struct.pack('<QiI', 0, 0, 0)
        self.mem[hdr(5)] = struct.pack('<QiI', self.source, 2, 2)
        self.mem[hdr(6)] = struct.pack('<QiI', 0x5, 3, 3)          # implausible pointer
        r = scan_registry(self.reader, self.entity, self.world, [(0x90000, b'identity')], entries=8)
        self.assertEqual(r['entity_entries'], [5])
        self.assertEqual(r['entries'][5]['entity_indices'], [1])
        self.assertEqual(r['entries'][6]['status'], 'invalid')
        self.assertEqual(r['entries'][0]['status'], 'empty')

    def test_before_simulation_actor_receiver(self):
        q = lambda v: struct.pack('<Q', v)
        actor, atable = 0x790000, self.base + 0x1e7a350
        self.mem.update({self.graph + 0x4ca0: q(self.base + 0x1ec7f38),
                         self.graph + 0x4e60: q(self.base + 0x8b9750),
                         self.world + 0x770: struct.pack('<QiI', 0x7b0000, 2, 4),
                         self.graph + 0x4e38: struct.pack('<Qii', 0x7c0000, 1, 2),
                         0x7b0000: struct.pack('<2Q', self.other, actor),
                         0x7c0000: struct.pack('<2Q', self.other, actor),
                         actor: q(atable) + bytes(8) + q(self.entity),
                         atable + 0x270: q(self.base + 0x564ee0)})
        r = capture_motion_membership(self.reader, self.entity, self.world, self.base,
                                      [(0x90000, b'identity')], job=0x4ca0, entry=0x770, actor=actor)
        self.assertEqual((r['batch'], r['registry_entry']), ('Physic::BeforeSimulation', 25))
        self.assertEqual((r['actor_source_indices'], r['owned_source_indices']), ([1], [1]))
        row = r['receivers'][1]
        self.assertEqual((row['table_rva'], row['motion_method_rva'], row['storage_indices'],
                          row['unclaimed_prefix_indices']), (0x1e7a350, 0x564ee0, [1], []))
        self.assertEqual(r['receivers'][0]['unclaimed_prefix_indices'], [0])

    def test_animation_event_batch_uses_its_own_thunk_and_slot(self):
        q = lambda v: struct.pack('<Q', v)
        self.mem[self.graph + 0x43d8] = q(self.base + 0x1ec7f38)
        self.mem[self.graph + 0x4598] = q(self.base + 0x732320)
        self.mem[self.graph + 0x4570] = self.mem[self.graph + 0x4c70]
        self.mem[self.world + 0x570] = self.mem[self.world + 0x730]
        self.mem[self.ptable + 0x278] = q(self.base + 0x38a590)
        self.mem[self.otable + 0x278] = q(self.base + 0x123456)
        def capture():
            return capture_motion_membership(self.reader, self.entity, self.world,
                self.base, [(0x90000, b'identity')], job=0x43d8, entry=0x570)
        r = capture()
        self.assertEqual((r['batch'], r['registry_entry'], r['dispatch_slot']),
                         ('DispatchAnimEvents', 17, 0x278))
        self.assertEqual(r['entity_motion_method_rva'], 0x38a590)
        self.assertEqual(r['receivers'][0]['motion_method_rva'], 0x123456)
        self.assertFalse(r['callback_execution_established'])
        self.mem[self.graph + 0x4598] = q(self.base + 0x8b9750)
        with self.assertRaisesRegex(ValueError, 'callback mismatch'):
            capture()

    def test_registry_scan_reports_owned_components(self):
        q = lambda v: struct.pack('<Q', v)
        comp, ctable = 0x780000, self.base + 0x1f20000
        hdr = lambda i: self.world + 0x130 + i * 0x40
        for i in range(4):
            self.mem[hdr(i)] = struct.pack('<QiI', 0, 0, 0)
        self.mem[hdr(2)] = struct.pack('<QiI', 0x7a0000, 2, 4)
        self.mem[0x7a0000] = struct.pack('<2Q', self.other, comp)
        self.mem[comp] = q(ctable) + bytes(8) + q(self.entity)
        self.mem[comp + 16] = q(self.entity)
        self.mem[self.other] = q(self.otable) + bytes(8) + q(0x800000)
        self.mem[self.other + 16] = q(0x800000)
        self.mem[ctable + 0x270] = q(self.base + 0x920000)
        r = scan_registry(self.reader, self.entity, self.world, [(0x90000, b'identity')],
                          entries=4, image_base=self.base)
        self.assertEqual(r['owned_entries'], [2])
        self.assertEqual(r['entries'][2]['owned'],
                         [dict(index=1, table_rva=0x1f20000, motion_method_rva=0x920000)])
        self.assertEqual(r['entity_entries'], [])


if __name__ == '__main__':
    unittest.main()
