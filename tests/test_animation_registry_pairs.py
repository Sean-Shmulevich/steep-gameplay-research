import json
from pathlib import Path
import unittest
from reference.animation_registry_pairs import finalize_construction_pair


class RegistryPairTests(unittest.TestCase):
    def test_original_finalization(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/registry_pairs_validation.json').read_text())
        for sample in receipt['samples']:
            self.assertEqual(finalize_construction_pair(**sample['inputs']),sample['result'])

    def test_swap_removal_changes_next_resolution(self):
        from reference.animation_target_resolution import resolve_registered_target
        rows=[['remove','a'],['wanted','first'],['wanted','last']]
        result=finalize_construction_pair(rows,identity='remove',target='a',target_word=1)
        resolved=resolve_registered_target(key='wanted',enabled=True,pairs=result['pairs'],
            secondary_holder_present=False,secondary_target=None,fallback_target=None)
        self.assertEqual(resolved['value'],'last')
        self.assertEqual(rows[0],['remove','a'])

    def test_original_connected_registration(self):
        from reference.animation_registry_pairs import finalize_and_register
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/registry_registration_validation.json').read_text())
        for sample in receipt['samples']:
            args=dict(sample['inputs'])
            args['identity_to_target']={int(k):v for k,v in args['identity_to_target'].items()}
            result=finalize_and_register(**args)
            self.assertEqual(json.loads(json.dumps(result)),sample['result'])

    def test_existing_different_target_suppresses_registration(self):
        from reference.animation_registry_pairs import finalize_and_register
        result=finalize_and_register([['id','new']],identity='id',target='new',
            target_word=0,enabled=True,secondary_holder_present=False,
            secondary_target=None,target_to_identity={},identity_to_target={'id':'old'})
        self.assertFalse(result['registered'])
        self.assertEqual(result['target_word'],0)
        self.assertEqual(result['identity_to_target'],{'id':'old'})
