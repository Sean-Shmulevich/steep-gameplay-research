import json
from pathlib import Path
import unittest
from reference.object_pointer_cache import finalize_pointer_cache

class ActionKitIdentityTests(unittest.TestCase):
    def test_constructor_receipt_starts_with_empty_cache(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/action_kit_identity_validation.json').read_text())
        self.assertEqual((r['type_name'], r['object_size'], r['cases']), ('ActionKit', 168, 32))
        self.assertTrue(r['metadata_constructor_and_finalizer_join'])
        self.assertTrue(r['constructor_vtable_reader_and_type_getter_join'])
        for row in r['rows']:
            self.assertEqual((row['source_count'], row['cache_count'], row['source_pointer'], row['cache_pointer']), (0, 0, 0, 0))
            self.assertTrue(row['lock_initialization_requested'])
            self.assertTrue(finalize_pointer_cache([], 0, [])['rebuilt'])
