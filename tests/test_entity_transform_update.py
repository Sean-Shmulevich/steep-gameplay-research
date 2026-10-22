import json
from pathlib import Path
import unittest
from reference.entity_transform_update import TransformEntity, update_entity_transform


class EntityTransformUpdateTests(unittest.TestCase):
    def test_native_mutating_collection_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/entity_transform_validation.json').read_text())
        self.assertEqual(receipt['cases'], 18)
        for sample in receipt['samples']:
            with self.subTest(sample=sample):
                depth = sample['initial_depth']
                entity = TransformEntity(bytes(64), list(range(sample['pre_count'])),
                    lock_owner=7 if depth else None, lock_depth=depth)
                seen = []
                def record(kind, entity):
                    self.assertEqual((entity.lock_owner, entity.lock_depth), (7, depth+1))
                    seen.append(dict(kind=kind, transform='old' if entity.transform == bytes(64) else 'new'))
                def notify(kind, component, entity):
                    record(kind, entity)
                    if kind == 'pre':
                        entity.components = list(range(sample['replacement_count']))
                update_entity_transform(entity, bytes([1])*64, thread_id=7,
                    notify=notify, publish_cache=lambda e: record('cache', e))
                self.assertEqual(seen, sample['events'])
                self.assertEqual(entity.lock_depth, depth)
                self.assertEqual(entity.lock_owner, 7 if depth else None)
                self.assertEqual((entity.pre_flag, entity.post_flag), (0, 1))

    def test_contended_and_accessor_paths_refuse_before_callbacks(self):
        entity = TransformEntity(bytes(64), lock_owner=3, lock_depth=1)
        def fail(*args): self.fail('must refuse before callback')
        with self.assertRaises(RuntimeError):
            update_entity_transform(entity, bytes(64), thread_id=7, notify=fail, publish_cache=fail)
        entity.lock_owner = None; entity.lock_depth = 0; entity.accessor_present = True
        with self.assertRaises(NotImplementedError):
            update_entity_transform(entity, bytes(64), thread_id=7, notify=fail, publish_cache=fail)

    def test_authored_exception_cleanup_does_not_rollback_copy(self):
        entity = TransformEntity(bytes(64))
        def fail(entity): raise RuntimeError('synthetic cache failure')
        with self.assertRaises(RuntimeError):
            update_entity_transform(entity, bytes([1])*64, thread_id=7,
                notify=lambda *args: None, publish_cache=fail)
        self.assertEqual(entity.transform, bytes([1])*64)
        self.assertEqual((entity.lock_owner, entity.lock_depth), (None, 0))
        self.assertEqual(entity.post_flag, 0)

    def test_original_accessor_gate_and_copy_before_services(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/transform_propagation_gate_validation.json').read_text())
        self.assertEqual(receipt['cases'], 1036)
        for sample in receipt['samples']:
            entity = TransformEntity(bytes(64), accessor_present=sample['present'])
            events = []
            def valid(e):
                self.assertEqual(e.transform, bytes(range(64)))
                events.append('validity')
                return sample['valid']
            def propagate(e, flags):
                self.assertEqual(e.transform, bytes(range(64)))
                self.assertEqual(flags, sample['flags'])
                events.append('propagate')
            update_entity_transform(entity, bytes(range(64)), thread_id=7,
                notify=lambda *args: None, publish_cache=lambda e: events.append('cache'),
                flags=sample['flags'], descriptor_valid=valid, propagate=propagate)
            self.assertEqual(events, sample['events']+['cache'])

    def test_pre_callback_can_add_accessor_and_forced_path_skips_validity(self):
        entity = TransformEntity(bytes(64), ['component'])
        events = []
        def notify(phase, component, e):
            events.append(phase)
            if phase == 'pre': e.accessor_present = True
        def unexpected(e): self.fail('forced path must skip validity')
        update_entity_transform(entity, bytes(64), thread_id=7, notify=notify,
            publish_cache=lambda e: events.append('cache'), descriptor_valid=unexpected,
            propagate=lambda e, flags: events.append('propagate'))
        self.assertEqual(events, ['pre', 'propagate', 'cache', 'post'])
