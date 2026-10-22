import json
from pathlib import Path
import unittest
from reference.animation_selection_mask import *
from reference.animation_temporary import prepare_temporary_bank, cleanup_temporary_bank


class SelectionMaskTests(unittest.TestCase):
    def test_instruction_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/selection_mask_validation.json').read_text())
        self.assertEqual(receipt['cases'],36)
        for r in receipt['rows']:
            self.assertEqual(copy_selection_mask(None,r['a']),r['copy'])
            self.assertEqual(intersect_selection_masks(r['a'],r['b']),r['intersection'])
            self.assertEqual(union_selection_masks(r['a'],r['b']),r['union'])
            self.assertEqual(is_active_selection_mask(r['a']),r['active'])
            self.assertEqual(acquire_selection_mask(r['a']),r['acquired'])
        self.assertEqual(acquire_selection_mask(),65535)

    def test_lifecycle_uses_mask_value_without_heap_copy(self):
        temporary=dict(bank=None,bank_owner=None,owned=False,pending=None,
                       binding=dict(value=None,owner=None))
        context=dict(bank_owner='pool',auxiliary_owner='aux',mode=1,
                     binding=dict(value=0x8001,owner='pool'),metadata_base='base')
        requests=[]
        prepare_temporary_bank(temporary,context,release_binding=release_selection_mask,
            copy_selection_mask=copy_selection_mask,release_bank=lambda *a:self.fail(),
            acquire_bank=lambda *a:(requests.append(a) or 'pose'))
        self.assertEqual(requests,[('pool',0x8001,1,0)])
        releases=[]
        cleanup_temporary_bank(temporary,recycle_pending=lambda *a:self.fail(),
            release_binding=release_selection_mask,release_bank=lambda *a:releases.append(a))
        self.assertEqual(releases,[('pool','pose')])
        self.assertEqual(context['binding']['value'],0x8001)
