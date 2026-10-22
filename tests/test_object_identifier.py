import json
from pathlib import Path
import unittest
from reference.object_identifier import resolve_object_identifier as resolve

class ObjectIdentifierTests(unittest.TestCase):
    def test_original_resolver_receipt(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/object_identifier_validation.json').read_text())
        self.assertEqual(r['cases'], 128)
        for row in r['rows']:
            self.assertEqual(resolve(**row['inputs']), row['result'])

    def test_mismatched_null_overlay_suppresses_all_fallback(self):
        r = resolve(77, True, [[88, 0], [77, 11]], 22, 33)
        self.assertEqual(r['object'], 0)
        self.assertEqual(r['overlay_index'], 0)
        self.assertEqual(r['lookups'], ['overlay'])

    def test_first_matching_overlay_wins(self):
        self.assertEqual(resolve(77, True, [[77, 11], [77, 22]], 33, 44)['object'], 11)

    def test_map_fallback_only_after_overlay_miss_and_null_record_target(self):
        self.assertEqual(resolve(77, True, [[88, 11]], 22, 33)['lookups'],
                         ['overlay', 'record_map'])
        r = resolve(77, True, [[88, 11]], 0, 33)
        self.assertEqual(r['lookups'], ['overlay', 'record_map', 'fallback_map'])
        self.assertEqual(r['object'], 33)
        self.assertFalse(r['lifetime_retained'])

    def test_disabled_and_zero_id_do_not_search(self):
        for identifier, enabled in ((0, True), (77, False)):
            r = resolve(identifier, enabled, [[77, 11]], 22, 33)
            self.assertEqual((r['object'], r['lookups']), (0, []))
