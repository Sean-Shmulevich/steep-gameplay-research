from copy import deepcopy
import math
import unittest

from engine.animation_skeleton import assemble_initial_skeleton
from reference.animation_hierarchy import reconcile_current_hierarchy


class SkeletonAssemblyTests(unittest.TestCase):
    def inputs(self):
        return dict(source_records=[dict(parent_index=65535 if i==0 else 0,
                     skip_span=0, source_index=9-i, linked_index=None,
                     key=100+i, link_mode=7) for i in range(3)],
                    backing_records=[bytes([255])*32 for _ in range(3)],
                    selector=4, overrides={102:7}, owner_visible=True, owner_value=0,
                    runtime_entries=[(100,0),(101,1),(102,2)], owner_entries=[],
                    preset_keys=dict(standard=[101,101,999], extended=[102], alternate=[100]))

    def test_selection_duplicates_and_preserved_bits(self):
        args=self.inputs();before=deepcopy(args)
        result=assemble_initial_skeleton(**args)
        self.assertEqual(args,before)
        self.assertEqual(result['indices'],[1,1])
        self.assertEqual([r['flags'] for r in result['rows']],[0xd0,0xd8,0xf0])
        self.assertEqual([r['linked_index'] for r in result['rows']],[0,1,2])
        self.assertFalse(result['evidence']['native_full_assembly_validated'])

    def test_composed_metadata_drives_direction_and_rank_skip(self):
        assembled=assemble_initial_skeleton(**self.inputs())
        q=(0.,0.,0.,1.)
        current=[((10.,0.,0.,0.),q),((15.,0.,0.,0.),q),((90.,0.,0.,0.),q)]
        primary=[((1.,0.,0.,0.),q),((2.,0.,0.,0.),q),((3.,0.,0.,0.),q)]
        result=reconcile_current_hierarchy(current,primary,assembled['metadata'],5,
                                           lambda x:1/math.sqrt(x))
        self.assertEqual(result['visited'],[dict(index=0,destination='current'),dict(index=1,destination='primary')])
        self.assertEqual(result['skipped'],[[2,3]])
        self.assertEqual(result['current'][0][0][0],1.)
        self.assertEqual(result['primary'][1][0][0],14.)
        self.assertEqual(result['current'][2],current[2])
        self.assertEqual(result['primary'][2],primary[2])

    def test_owner_table_is_independent_and_hidden_owner_selects_nothing(self):
        args=self.inputs();args['owner_entries']=[(0xb95094e1,6)]
        self.assertEqual(assemble_initial_skeleton(**args)['indices'],[2])
        args['owner_visible']=False;args['owner_value']=2
        result=assemble_initial_skeleton(**args)
        self.assertEqual(result['indices'],[])
        self.assertEqual(result['default_rank'],1)

    def test_missing_storage_and_invalid_mapping_fail_without_mutation(self):
        args=self.inputs();args['backing_records']=[]
        with self.assertRaises(ValueError):assemble_initial_skeleton(**args)
        args=self.inputs();args['runtime_entries']=[(101,8)];before=deepcopy(args)
        with self.assertRaises(ValueError):assemble_initial_skeleton(**args)
        self.assertEqual(args,before)
