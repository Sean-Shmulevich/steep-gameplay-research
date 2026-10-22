import json
from pathlib import Path
import struct
import unittest
from reference.attachment_transform_setup import initialize_attachment_transform


def packed(matrix):
    return struct.pack('<16f', *(x for row in matrix for x in row))


class AttachmentTransformSetupTests(unittest.TestCase):
    def test_original_setup_with_mutating_parent_and_failed_validity(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/attachment_setup_order_validation.json').read_text())
        self.assertEqual(receipt['cases'], 64)
        for sample in receipt['samples']:
            events = []; reads = []; seed_calls = []; local = []; published = []
            def parent():
                value = [row[:] for row in sample['parent']]
                if reads and sample['changed']: value[3][0] += 10
                reads.append(value); events.append('parent_read')
                return value
            def valid():
                events.append('validity'); return sample['valid']
            def seed(value):
                i = len(seed_calls); seed_calls.append(value)
                self.assertEqual(value, sample['seed_inputs'][i])
                return sample['seeds'][i]
            def publish(kind, packet):
                self.assertIs(packet['first_transform'], packet['second_transform'])
                self.assertEqual(packet['flags'], 31)
                events.append(kind); published.append(packet['first_transform'])
            outcome = initialize_attachment_transform(current_transform=lambda: receipt['world'],
                explicit_offset=receipt['offset'] if sample['explicit'] else None,
                get_parent=parent, descriptor_valid=valid, store_local=local.append,
                publish_entity=lambda p: publish('entity',p),
                propagate_child=lambda p: publish('child',p), reciprocal_seed=seed)
            self.assertEqual(events, sample['events'])
            self.assertEqual(len(seed_calls), 0 if sample['explicit'] else 4)
            if local: self.assertEqual(packed(local[0]), packed(sample['local']))
            else: self.assertEqual(packed(sample['local']), bytes(64))
            if published: self.assertEqual(packed(published[0]), packed(sample['published']))
            else: self.assertEqual(outcome, 'descriptor_rejected')

    def test_original_inner_acceptance_checks(self):
        from reference.attachment_transform_setup import plan_attachment_acceptance
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/attachment_acceptance_validation.json').read_text())
        self.assertEqual(receipt['cases'], 48)
        for sample in receipt['samples']:
            result = plan_attachment_acceptance(**sample['inputs'])
            self.assertEqual(result['accepted'], sample['accepted'])
            self.assertEqual(result['permission_queried'], sample['permission_queried'])

    def test_null_owner_is_not_an_owner_mismatch(self):
        from reference.attachment_transform_setup import plan_attachment_acceptance
        result = plan_attachment_acceptance(child='c', parent='p', parent_link=None,
            child_owner=None, parent_owner='world', permission=True)
        self.assertTrue(result['accepted'])
        self.assertTrue(result['permission_queried'])

    def test_concrete_entity_permission_receipt(self):
        from reference.attachment_transform_setup import plan_entity_attachment_permission
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/attachment_permission_validation.json').read_text())
        self.assertEqual(receipt['cases'], 32)
        for sample in receipt['samples']:
            inputs = {key:sample[key] for key in ('child_group','parent_group','contains_other','child_bit','parent_bit')}
            self.assertEqual(plan_entity_attachment_permission(**inputs),
                             dict(accepted=sample['accepted'], events=sample['events']))

    def test_original_flag_propagation_order_and_duplicates(self):
        from reference.attachment_transform_setup import plan_attachment_flag_propagation
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/attachment_flag_propagation_validation.json').read_text())
        self.assertEqual(receipt['cases'], 32)
        names = ['root','child','linked']
        for sample in receipt['samples']:
            result = plan_attachment_flag_propagation('root',sample['target'],
                dict(zip(names,sample['initial'])), {'root':['child']},
                {'root':['linked','child']} if sample['skeleton_links'] else {})
            self.assertEqual([result['bits'][x] for x in names],sample['result'])
            self.assertEqual([e['event']+'_'+e['entity'] for e in result['events']],sample['events'])

    def test_cycle_budget_is_authored_not_native_cycle_detection(self):
        from reference.attachment_transform_setup import plan_attachment_flag_propagation
        with self.assertRaises(ValueError):
            plan_attachment_flag_propagation('a',1,{'a':1},{'a':['a']},{},max_visits=4)
