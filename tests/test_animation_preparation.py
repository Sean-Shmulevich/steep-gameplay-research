import json
from pathlib import Path
import struct
import unittest
from engine.animation_preparation import prepare_animation


class PreparationIntegrationTests(unittest.TestCase):
    def test_full_original_call_chain(self):
        self.check_receipt('preparation_integrated_validation.json')

    def test_visible_context_call_chain(self):
        self.check_receipt('preparation_context_validation.json')

    def test_visible_context_switch_call_chain(self):
        self.check_receipt('preparation_context_switch_validation.json')

    def check_receipt(self, filename):
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host' / filename).read_text())
        for sample in receipt['samples']:
            seeds=iter(sample['rsqrt_seeds']);calls=iter(sample['math_services'])
            def trig(name,x):
                row=next(calls);self.assertEqual((name,x),(row['name'],row['input']));return row['output']
            result=prepare_animation(**sample['inputs'],resolve_context=lambda token:{1:sample.get('active_context'),2:sample.get('replacement_context')}.get(token),
                reciprocal_sqrt=lambda _:next(seeds),acos=lambda x:trig('acos',x),sin=lambda x:trig('sin',x))
            self.assertEqual(json.loads(json.dumps(result)),sample['result'])
            for bank in ('current','primary'):
                def pack(rows):return b''.join(struct.pack('<8f',*(list(p)+list(q))) for p,q in rows)
                self.assertEqual(pack(result[bank]['records']),pack(sample['result'][bank]['records']))
            self.assertEqual(list(seeds),[]);self.assertEqual(list(calls),[])
