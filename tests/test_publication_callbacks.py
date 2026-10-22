import json
from pathlib import Path
import unittest
from reference.publication_callbacks import plan_publication_callbacks as plan

class PublicationCallbackTests(unittest.TestCase):
    def test_original_dispatch_receipt(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/publication_callbacks_validation.json').read_text())
        self.assertEqual(r['cases'], 256)
        for row in r['rows']:
            self.assertEqual(plan(row['categories'], row['skip_mask']), row['calls'])

    def test_skip_mask_phase_matrix(self):
        cats = [dict(flags=f, entries=[dict(object=11, tag=f, secondary=False)]) for f in range(4)]
        self.assertEqual([c['category'] for c in plan(cats, 2)], [0, 1])
        self.assertEqual([c['category'] for c in plan(cats, 1)], [0, 2])

    def test_reverse_entry_order_and_secondary_pairing(self):
        cats = [dict(flags=0, entries=[dict(object=11, tag=1, secondary=True),
                                      dict(object=22, tag=2, secondary=False)])]
        self.assertEqual([(c['object'], c['callback']) for c in plan(cats, 2)],
                         [(22, 'primary'), (11, 'primary'), (11, 'secondary')])

    def test_null_receiver_skips_both_callbacks(self):
        self.assertEqual(plan([dict(flags=0, entries=[dict(object=0, tag=1, secondary=True)])], 1), [])
