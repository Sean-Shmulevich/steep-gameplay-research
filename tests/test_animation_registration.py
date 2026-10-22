import json
from pathlib import Path
import unittest
from reference.publication_callbacks import plan_publication_callbacks

class AnimationRegistrationTests(unittest.TestCase):
    def test_registered_routes_dispatch_before_handoff(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/animation_registration_validation.json').read_text())
        self.assertEqual(r['cases'], 3)
        for row in r['rows']:
            categories = [dict(flags=row['category_flags'], entries=[row['entry']])]
            calls = plan_publication_callbacks(categories, 2)
            self.assertEqual([c['callback'] for c in calls],
                             ['primary', 'secondary'] if row['secondary_registered'] else ['primary'])
            self.assertEqual(plan_publication_callbacks(categories, 1), [])
            self.assertTrue(row['before_handoff'])
            self.assertFalse(row['after_handoff'])
