import json
from pathlib import Path
import unittest
from reference.animation_mask_preparation import prepare_blend_mask


class MaskPreparationTests(unittest.TestCase):
    def test_original_instruction_receipt(self):
        r=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/blend_mask_preparation_validation.json').read_text())
        self.assertEqual(r['cases'],96)
        for row in r['rows']:
            with self.subTest(row=row):
                data=bytearray(range(32));count=row['count']
                values=memoryview(data)[:count] if row['alias'] else bytes(range(100,100+count))
                profile=dict(descriptors=[dict(offset=o,kind=15) for o in r['offsets']]) if row['profile_present'] else None
                visited=prepare_blend_mask(dict(indices=r['indices'],mode_values=[values]*3),
                    dict(data=data,profile=profile),row['mode'])
                self.assertEqual(list(data),row['output']);self.assertEqual(visited,row['visited'])

    def test_gates_do_not_require_payload(self):
        self.assertEqual(prepare_blend_mask({},dict(profile=None),0),[])
        self.assertEqual(prepare_blend_mask({},dict(profile={}),9),[])

    def test_invalid_offset_refused(self):
        with self.assertRaises(ValueError):
            prepare_blend_mask(dict(indices=[0],mode_values=[b'a']*3),
                dict(profile=dict(descriptors=[dict(offset=4)]),data=bytearray(4)),0)
