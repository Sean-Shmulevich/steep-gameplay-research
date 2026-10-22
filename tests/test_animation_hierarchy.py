import json
from pathlib import Path
import struct
import unittest
from reference.animation_hierarchy import compose_primary_hierarchy


class HierarchyTests(unittest.TestCase):
    def test_original_full_wrapper_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/primary_hierarchy_validation.json').read_text())
        def packed(records):
            return b''.join(struct.pack('<8f',*(list(p)+list(q))) for p,q in records)
        for sample in receipt['samples']:
            seeds=iter(sample['rsqrt_seeds'])
            result=compose_primary_hierarchy(**sample['inputs'],reciprocal_sqrt=lambda _:next(seeds))
            self.assertEqual(packed(result['records']),packed(sample['result']['records']))
            self.assertEqual(result['visited'],sample['result']['visited'])
            self.assertEqual(result['skipped'],sample['result']['skipped'])
            self.assertEqual(list(seeds),[])

    def test_original_current_processing_receipt(self):
        from reference.animation_hierarchy import reconcile_current_hierarchy
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/current_hierarchy_validation.json').read_text())
        def packed(records):
            return b''.join(struct.pack('<8f',*(list(p)+list(q))) for p,q in records)
        for sample in receipt['samples']:
            seeds=iter(sample['rsqrt_seeds'])
            result=reconcile_current_hierarchy(**sample['inputs'],reciprocal_sqrt=lambda _:next(seeds))
            for bank in ('current','primary'):
                self.assertEqual(packed(result[bank]),packed(sample['result'][bank]))
            self.assertEqual(result['visited'],sample['result']['visited'])
            self.assertEqual(result['skipped'],sample['result']['skipped'])
            self.assertEqual(list(seeds),[])

    def test_zero_prefix_still_processes_nonempty_root(self):
        from reference.animation_hierarchy import reconcile_current_hierarchy
        import math
        current=[([9.,0.,0.,1.],[0.,0.,0.,1.])]*2
        primary=[([2.,0.,0.,1.],[0.,0.,0.,1.])]*2
        metadata=[dict(parent=0,rank=7,skip_span=0,current_authoritative=False)]*2
        result=reconcile_current_hierarchy(current,primary,metadata,0,
            lambda n:1/math.sqrt(n),processed_count=0)
        self.assertEqual(result['visited'],[dict(index=0,destination='current')])
        self.assertEqual(result['current'][0][0][0],2.)
        self.assertEqual(result['current'][1],(tuple(current[1][0]),tuple(current[1][1])))
