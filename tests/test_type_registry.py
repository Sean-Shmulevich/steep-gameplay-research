import json
import unittest
from pathlib import Path

from reference.type_registry import radix_type_registry_lookup as lookup, UnsupportedRegistryNode


class RadixRegistryTests(unittest.TestCase):
    def test_original_branch_traversal(self):
        root = Path(__file__).resolve().parents[1]/'native/snow_host'
        for name, count in [('radix_branch_validation',1064),('radix_dense_chain_validation',64)]:
            receipt=json.loads((root/(name+'.json')).read_text())
            self.assertEqual(receipt['cases'],count)
            for row in receipt['rows']:
                self.assertEqual(lookup(row['nodes'],row['root'],row['key']),row['value'])

    def test_missing_and_unsupported_are_distinct(self):
        self.assertIsNone(lookup([{'kind':8}],0,0))
        for kind in [0,7,60,255]:
            with self.assertRaises(UnsupportedRegistryNode):lookup([{'kind':kind}],0,0)

    def test_single_value_preserves_zero_and_ignores_high_byte(self):
        self.assertEqual(lookup([{'kind':44,'prefix':123,'value':0}],0,123|(255<<56)),0)
        self.assertIsNone(lookup([{'kind':50,'prefix':123,'value':0}],0,122))

    def test_cycle_and_structural_validation(self):
        cyclic=[{'kind':15,'prefix':0,'labels':[0],'children':[0]}]
        with self.assertRaisesRegex(ValueError,'cyclic'):lookup(cyclic,0,0)
        with self.assertRaises(ValueError):lookup([{'kind':35,'children':[]}],0,0)
        with self.assertRaises(ValueError):lookup([{'kind':8}],0,-1)
        with self.assertRaises(ValueError):lookup([{'kind':8}],True,0)
        malformed=[{'kind':22,'prefix':0,'groups':[{'bitmap':1,'children':[]}]*8}]
        with self.assertRaisesRegex(ValueError,'population'):lookup(malformed,0,0)

    def test_root_only_dense_kind_is_rejected_as_child(self):
        nodes=[{'kind':15,'prefix':0,'labels':[0],'children':[1]}, {'kind':35,'children':[0]*256}]
        with self.assertRaises(UnsupportedRegistryNode):lookup(nodes,0,0)


class RadixLeafTests(unittest.TestCase):
    def test_original_multi_value_leaves_and_branch_join(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/radix_leaf_validation.json').read_text())
        self.assertEqual(receipt['cases'],3501)
        kinds=set(range(36,44))|set(range(51,60))
        self.assertEqual({r['node']['kind'] for r in receipt['rows']},kinds)
        self.assertEqual({r['node']['kind'] for r in receipt['rows'] if r['top_byte_branch']},kinds)
        for row in receipt['rows']:
            nodes=[row['node']]
            if row['top_byte_branch']:
                children=[1]*256;children[row['key']>>56]=2
                nodes=[{'kind':35,'children':children},{'kind':8},row['node']]
            self.assertEqual(lookup(nodes,0,row['key']),row['value'])

    def test_packed_duplicate_scan_is_not_forward_lower_bound(self):
        node={'kind':38,'prefix':0,'keys':[7]*8,'values':list(range(8))}
        self.assertEqual(lookup([node],0,7),7)
        node.update(kind=37)
        self.assertEqual(lookup([node],0,7),0)
        node.update(kind=59,keys=[7,7],values=[10,11])
        self.assertEqual(lookup([node],0,7),11)

    def test_prefix_and_inline_width_differ(self):
        array={'kind':36,'prefix':256,'keys':[7,8],'values':[10,11]}
        self.assertIsNone(lookup([array],0,7))
        self.assertEqual(lookup([array],0,263),10)
        inline={**array,'kind':51}
        self.assertEqual(lookup([inline],0,7|(123<<8)),10)

    def test_bitmap_groups_and_logical_zero_value(self):
        groups=[{'bitmap':0,'values':[]} for _ in range(4)]
        groups[3]={'bitmap':1<<63,'values':[0]}
        node={'kind':43,'prefix':0,'groups':groups}
        self.assertEqual(lookup([node],0,255),0)
        self.assertIsNone(lookup([node],0,254))
        self.assertIsNone(lookup([node],0,511))

    def test_leaf_inspection_bounds(self):
        for node in [
            {'kind':51,'keys':[0],'values':[0]},
            {'kind':59,'keys':[0,2**24],'values':[0,1]},
            {'kind':36,'prefix':0,'keys':[0]*14,'values':[0]*14},
            {'kind':37,'prefix':0,'keys':[2,1],'values':[0,1]},
            {'kind':51,'keys':[0,1],'values':[None,1]},
        ]:
            with self.assertRaises(ValueError):lookup([node],0,0)


class RadixLeafCursorTests(unittest.TestCase):
    def test_original_first_and_next_transitions(self):
        from reference.type_registry import radix_leaf_cursor
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/radix_leaf_cursor_validation.json').read_text())
        self.assertEqual(receipt['cases'],768)
        self.assertEqual({r['node']['kind'] for r in receipt['rows']},set(range(36,60)))
        for row in receipt['rows']:
            self.assertEqual(radix_leaf_cursor(row['node'],row['key'],advance=row['advance']),row['result'])

    def test_single_value_cursor_write_width_differs_from_comparison(self):
        from reference.type_registry import radix_leaf_cursor as cursor
        node={'kind':44,'prefix':0x1234,'value':9}
        self.assertEqual(cursor(node,0),{'key':0x34,'value':9})
        self.assertEqual(cursor(node,0x1234),{'key':0x1234,'value':9})
        self.assertEqual(cursor(node,0x1234,advance=True),{'key':0x1235,'value':None})

    def test_prefix_jump_and_exhaustion(self):
        from reference.type_registry import radix_leaf_cursor as cursor
        node={'kind':36,'prefix':0x1200,'keys':[3,7],'values':[0,1]}
        self.assertEqual(cursor(node,0),{'key':0x1203,'value':0})
        self.assertEqual(cursor(node,0x1203,advance=True),{'key':0x1207,'value':1})
        self.assertEqual(cursor(node,0x1207,advance=True),{'key':0x1208,'value':None})
        self.assertEqual(cursor(node,2**64-1,advance=True),{'key':0,'value':None})

    def test_packed_duplicate_selection_and_advancement(self):
        from reference.type_registry import radix_leaf_cursor as cursor
        node={'kind':59,'keys':[7,7],'values':[1,2]}
        self.assertEqual(cursor(node,7),{'key':7,'value':2})
        self.assertEqual(cursor(node,5),{'key':7,'value':1})
        self.assertEqual(cursor(node,7,advance=True),{'key':8,'value':None})
        with self.assertRaises(UnsupportedRegistryNode):cursor({'kind':15},0)
        with self.assertRaises(ValueError):cursor(node,0,advance=1)


class RadixTreeCursorTests(unittest.TestCase):
    def test_original_branch_iteration_and_decoded_api(self):
        from reference.type_registry import radix_type_registry_cursor
        from reference.registry_snapshot import decoded_type_registry_cursor
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/radix_tree_cursor_validation.json').read_text())
        self.assertEqual(receipt['cases'],3836)
        for row in receipt['rows']:
            nodes=receipt['trees'][row['tree']]
            result=radix_type_registry_cursor(nodes,0,row['key'],advance=row['advance'])
            self.assertEqual(result,row['result'])
            self.assertEqual(decoded_type_registry_cursor({'representation':'radix','root':0,'nodes':nodes},row['key'],advance=row['advance']),result)

    def test_exhausted_child_continues_at_sibling_minimum(self):
        from reference.type_registry import radix_type_registry_cursor as cursor
        nodes=[{'kind':15,'prefix':0,'labels':[1,3],'children':[1,2]},
               {'kind':44,'prefix':0x105,'value':0},
               {'kind':44,'prefix':0x307,'value':1}]
        self.assertEqual(cursor(nodes,0,0),{'key':0x105,'value':0})
        self.assertEqual(cursor(nodes,0,0x105,advance=True),{'key':0x307,'value':1})
        self.assertEqual(cursor(nodes,0,0x307,advance=True),{'key':0x308,'value':None})

    def test_minimum_rewrites_suffix_instead_of_carrying_prior_leaf(self):
        from reference.type_registry import radix_type_registry_cursor as cursor
        nodes=[{'kind':15,'prefix':0,'labels':[1,2],'children':[1,2]},
               {'kind':44,'prefix':0x1fe,'value':0},
               {'kind':44,'prefix':0x203,'value':1}]
        self.assertEqual(cursor(nodes,0,0x1fe,advance=True),{'key':0x203,'value':1})

    def test_initial_exact_and_next_are_distinct(self):
        from reference.type_registry import radix_type_registry_cursor as cursor
        nodes=[{'kind':50,'prefix':8,'value':0}]
        self.assertEqual(cursor(nodes,0,8),{'key':8,'value':0})
        self.assertEqual(cursor(nodes,0,8,advance=True),{'key':9,'value':None})
        self.assertEqual(cursor(nodes,0,2**64-1,advance=True),{'key':0,'value':None})
        with self.assertRaises(ValueError):cursor(nodes,0,-1,advance=True)

    def test_cycle_and_unsorted_iteration_labels_rejected(self):
        from reference.type_registry import radix_type_registry_cursor as cursor
        cyclic=[{'kind':15,'prefix':0,'labels':[0],'children':[0]}]
        with self.assertRaisesRegex(ValueError,'cyclic'):cursor(cyclic,0,0,advance=True)
        unsorted=[{'kind':15,'prefix':0,'labels':[2,1],'children':[1,1]}, {'kind':50,'prefix':1,'value':0}]
        with self.assertRaisesRegex(ValueError,'sorted'):cursor(unsorted,0,0,advance=True)
