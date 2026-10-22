import json
from pathlib import Path
import unittest
from reference.hierarchy_commands import drain_hierarchy_commands


class HierarchyCommandTests(unittest.TestCase):
    def test_original_queue_and_completion_gate(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/hierarchy_queue_validation.json').read_text())
        self.assertEqual(receipt['cases'],360)
        for sample in receipt['samples']:
            a=sample['inputs']
            with self.subTest(inputs=a):
                result=drain_hierarchy_commands(pending=a['pending'],deferred=a['deferred'],
                    record_targets=[0 if a['visible'] else None]*a['available'],
                    entity_bytes={0:a['entity_byte']},read_index=a['read_index'],capacity=a['capacity'])
                self.assertEqual(result.pop('reattach_targets'),[0]*sample['result']['events'].count('reattach'))
                result['entity_byte']=result.pop('entity_bytes')[0]
                self.assertEqual(result,sample['result'])

    def test_mismatched_budget_reprocesses_last_record_after_unlock(self):
        result=drain_hierarchy_commands(pending=2,deferred=0,record_targets=['a'],
            entity_bytes={'a':130},read_index=3,capacity=4)
        self.assertEqual(result['entity_bytes']['a'],128)
        self.assertEqual(result['reattach_targets'],['a'])
        self.assertEqual(result['events'],['enter','leave','process','enter','leave','process','reattach'])
        self.assertEqual(result['read_index'],0)

    def test_distinct_targets_and_invisible_records(self):
        values={'a':129,'b':2}
        result=drain_hierarchy_commands(pending=3,deferred=1,
            record_targets=['a',None,'b'],entity_bytes=values,read_index=0,capacity=3)
        self.assertEqual(result['entity_bytes'],{'a':128,'b':0})
        self.assertEqual(result['reattach_targets'],['a','b'])
        self.assertEqual(values,{'a':129,'b':2})

    def test_signed_budget_and_explicit_bound(self):
        args=dict(pending=0x80000000,deferred=0,record_targets=['a'],
                  entity_bytes={'a':1},read_index=0,capacity=1)
        self.assertEqual(drain_hierarchy_commands(**args)['remaining'],1)
        with self.assertRaisesRegex(ValueError,'budget'):
            drain_hierarchy_commands(**dict(args,pending=10,max_iterations=9))

    def test_original_full_ring_publication_branches(self):
        from reference.hierarchy_commands import full_ring_submission
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/hierarchy_full_queue_validation.json').read_text())
        self.assertEqual(receipt['cases'],36)
        for sample in receipt['samples']:
            self.assertEqual(full_ring_submission(**sample['inputs']),sample['result'])

    def test_full_submission_can_create_excess_processing_budget(self):
        from reference.hierarchy_commands import full_ring_submission
        published=full_ring_submission(count=1,capacity=1,write_index=0,deferred=1)
        drained=drain_hierarchy_commands(pending=0,deferred=published['deferred'],
            record_targets=['old'],entity_bytes={'old':1},read_index=0,capacity=1)
        self.assertFalse(published['record_published'])
        self.assertEqual(drained['events'].count('process'),2)
        self.assertEqual(drained['entity_bytes']['old'],127)
        self.assertEqual(drained['reattach_targets'],['old'])

    def test_original_queue_initialization_and_allocation_failures(self):
        from reference.hierarchy_commands import initial_hierarchy_queue
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/hierarchy_init_validation.json').read_text())
        self.assertEqual(receipt['cases'],8)
        for sample in receipt['samples']:
            args=dict(sample['inputs']);args.pop('backing_fill')
            self.assertEqual(initial_hierarchy_queue(**args),sample['result'])
        failed=initial_hierarchy_queue(ring_allocation_succeeds=False)
        self.assertTrue(failed['published'])
        self.assertEqual(failed['capacity'],0)

    def test_original_successful_and_full_publication_bookkeeping(self):
        from reference.hierarchy_commands import hierarchy_publication_state
        root=Path(__file__).resolve().parents[1]/'native/snow_host'
        for filename in ('hierarchy_publication_validation.json','hierarchy_full_queue_validation.json'):
            receipt=json.loads((root/filename).read_text())
            for sample in receipt['samples']:
                with self.subTest(file=filename,inputs=sample['inputs']):
                    self.assertEqual(hierarchy_publication_state(**sample['inputs']),sample['result'])

    def test_original_post_submission_byte_all_values(self):
        from reference.hierarchy_commands import hierarchy_submission_byte
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/hierarchy_submit_byte_validation.json').read_text())
        self.assertEqual(receipt['cases'],512)
        for sample in receipt['samples']:
            self.assertEqual(hierarchy_submission_byte(sample['before'],sample['descriptor_valid']),sample['after'])

    def test_same_final_byte_can_hide_different_completion_events(self):
        from reference.hierarchy_commands import hierarchy_submission_byte
        def consume(value):
            return drain_hierarchy_commands(pending=1,deferred=0,record_targets=['entity'],
                entity_bytes={'entity':value},read_index=0,capacity=1)
        producer_first=consume(hierarchy_submission_byte(0,True))
        consumer_first=consume(0)
        final_after_late_producer=hierarchy_submission_byte(consumer_first['entity_bytes']['entity'],True)
        self.assertEqual(producer_first['entity_bytes']['entity'],final_after_late_producer)
        self.assertEqual(producer_first['reattach_targets'],['entity'])
        self.assertEqual(consumer_first['reattach_targets'],[])


class HierarchyRouteTests(unittest.TestCase):
    def test_original_caller_routes(self):
        from reference.hierarchy_commands import hierarchy_transform_route
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/hierarchy_route_validation.json').read_text())
        self.assertEqual(receipt['cases'], 512)
        for sample in receipt['samples']:
            self.assertEqual(hierarchy_transform_route(sample['flags'],
                sample['descriptor_valid']), sample['route'])

    def test_invalid_descriptor_and_override_bypass_queue(self):
        from reference.hierarchy_commands import hierarchy_transform_route
        self.assertEqual(hierarchy_transform_route(1, False), 'direct_dispatch')
        self.assertEqual(hierarchy_transform_route(5, True), 'direct_dispatch')
        self.assertEqual(hierarchy_transform_route(0, True), 'compose_then_dispatch')
        self.assertEqual(hierarchy_transform_route(1, True), 'queued')

    def test_recovered_fx_constructor_defaults_route_by_validity(self):
        from reference.hierarchy_commands import hierarchy_transform_route
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/hierarchy_owner_validation.json').read_text())
        self.assertEqual(receipt['type_name'], 'FXSpawnedEntity')
        self.assertEqual(receipt['cases'], 4)
        for sample in receipt['samples']:
            self.assertEqual(hierarchy_transform_route(sample['flags'], True), 'queued')
            self.assertEqual(hierarchy_transform_route(sample['flags'], False), 'direct_dispatch')
