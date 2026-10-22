import json
from pathlib import Path
import unittest
from reference.animation_target_resolution import resolve_target


class TargetResolutionTests(unittest.TestCase):
    def test_original_wrapper_precedence(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/target_resolution_validation.json').read_text())
        for sample in receipt['samples']:
            self.assertEqual(resolve_target(**sample['inputs']),sample['result'])

    def test_present_null_primary_blocks_fallback(self):
        result=resolve_target(key_present=True,enabled=True,primary_entry_present=True,
            primary_value=None,secondary_value='secondary',fallback_value='fallback')
        self.assertEqual(result,dict(value=None,source='primary',events=['lock','primary_lookup','unlock']))

    def test_original_connected_lookup_services(self):
        from reference.animation_target_resolution import resolve_registered_target
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/registered_target_validation.json').read_text())
        for sample in receipt['samples']:
            self.assertEqual(resolve_registered_target(**sample['inputs']),sample['result'])

    def test_unrelated_null_row_stops_before_matching_row(self):
        from reference.animation_target_resolution import resolve_registered_target
        result=resolve_registered_target(key='wanted',enabled=True,
            pairs=[['other',None],['wanted','live']],secondary_holder_present=True,
            secondary_target='secondary',fallback_target='fallback')
        self.assertEqual(result['primary_index'],0)
        self.assertIsNone(result['value'])
        self.assertEqual(result['source'],'primary')
