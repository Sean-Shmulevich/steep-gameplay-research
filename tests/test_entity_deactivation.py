import json
from pathlib import Path
import unittest
from reference.entity_deactivation import plan_entity_deactivation


class EntityDeactivationTests(unittest.TestCase):
    def test_original_lifecycle_order(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/entity_deactivation_validation.json').read_text())
        self.assertEqual(receipt['cases'],192)
        for sample in receipt['samples']:
            with self.subTest(inputs=sample['inputs']):
                self.assertEqual(plan_entity_deactivation(**sample['inputs']),sample['result'])

    def test_registry_lock_starts_after_transform_teardown(self):
        result=plan_entity_deactivation(component_count=2,extra_component=True,
            registry_matches=True,registry_contains_entity=False,task_present=True,state_byte=0)
        names=[e['event'] for e in result['events']]
        self.assertLess(names.index('transform_teardown'),names.index('registry_enter'))
        self.assertNotIn('registry_remove',names)
        self.assertTrue(result['registry_link_cleared'])
        self.assertEqual(result['state_byte_after'],255)

    def test_other_registry_is_not_cleared(self):
        result=plan_entity_deactivation(component_count=0,extra_component=False,
            registry_matches=False,registry_contains_entity=True,task_present=False,state_byte=1)
        self.assertFalse(result['registry_link_cleared'])
        self.assertEqual(result['events'],[dict(event='transform_teardown'),dict(event='tail_service')])

    def test_original_drain_with_base_entity_dispatch(self):
        from reference.entity_deactivation import plan_entity_collection_drain
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/entity_drain_validation.json').read_text())
        self.assertEqual(receipt['cases'],30)
        for sample in receipt['samples']:
            with self.subTest(inputs=sample['inputs'],state=sample['state_byte']):
                self.assertEqual(plan_entity_collection_drain(**sample['inputs']),sample['events'])

    def test_empty_and_duplicate_drains_preserve_lock_and_dispatch_rules(self):
        from reference.entity_deactivation import plan_entity_collection_drain
        empty=plan_entity_collection_drain([],False)
        self.assertEqual([e['event'] for e in empty],['enter','leave','temporary_release'])
        repeated=plan_entity_collection_drain([7,None,7],False)
        self.assertEqual([e['entity'] for e in repeated if e['event']=='lifecycle'],[7,7])
