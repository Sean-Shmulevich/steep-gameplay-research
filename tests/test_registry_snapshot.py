import unittest

from reference.registry_snapshot import decode_type_registry as decode, decoded_type_registry_lookup as lookup
from reference.type_registry import UnsupportedRegistryNode


class RegistrySnapshotTests(unittest.TestCase):
    def setUp(self):
        self.memory=bytearray(65536)
        self.reads=[]

    def read(self,address,size):
        self.reads.append((address,size))
        return bytes(self.memory[address:address+size])

    def word(self,address,value):
        self.memory[address:address+8]=value.to_bytes(8,'little')

    def node(self,address,kind,word=0,prefix=0):
        self.word(address,word)
        self.word(address+8,prefix|(kind<<56))

    def test_null_never_reads_or_resolves(self):
        def forbidden(*args):raise AssertionError('unexpected callback')
        snapshot=decode(forbidden,0,forbidden)
        self.assertEqual(snapshot,{'representation':'null','read_calls':0,'bytes_read':0})
        self.assertIsNone(lookup(snapshot,2**64-1))

    def test_compact_padding_and_explicit_identity_mapping(self):
        # Four keys: header at word 0, keys at 1..4, values start at word 6.
        self.word(0x1100,3)
        for i,k in enumerate([0,4,2**63,2**64-1]):self.word(0x1108+8*i,k)
        for i,v in enumerate([90,91,92,93]):self.word(0x1130+8*i,v)
        snapshot=decode(self.read,0x1101,lambda raw:raw-90)
        self.assertEqual(snapshot['values'],[0,1,2,3])
        self.assertEqual(lookup(snapshot,2**64-1),3)
        self.assertEqual(lookup(snapshot,0),0)
        self.assertIsNone(lookup(snapshot,2))
        self.assertEqual(snapshot['bytes_read'],sum(n for _,n in self.reads))

    def test_dense_to_bitmap_to_inline_packed_leaf(self):
        self.node(0x1108,35,0x2005)
        for i in range(256):self.node(0x2000+16*i,8)
        self.node(0x2010,27,0x4003)
        self.word(0x4010,1<<31)
        self.word(0x4018,0x5005)
        self.node(0x5000,59,0x6003)
        self.memory[0x5008:0x500e]=bytes([1,2,3,3,4,5])
        self.word(0x6000,90);self.word(0x6008,91)
        snapshot=decode(self.read,0x1103,lambda raw:raw-90)
        query=(1<<56)|(63<<48)|0x030201
        self.assertEqual(lookup(snapshot,query),0)
        self.assertEqual(lookup(snapshot,(query&~0xffffff)|0x050403),1)
        self.assertIsNone(lookup(snapshot,query^(1<<56)))
        self.assertEqual(len(snapshot['nodes']),258)

    def test_packed_seven_byte_array_layout_boundary(self):
        self.node(0x1108,42,0x2005,prefix=25)
        keys=list(range(25))+[2**56-1]
        for i,key in enumerate(keys):self.memory[0x2000+7*i:0x2007+7*i]=key.to_bytes(7,'little')
        # Count 26 moves the values to word 30, beyond the key payload.
        for i in range(26):self.word(0x2000+240+8*i,100+i)
        snapshot=decode(self.read,0x1103,lambda raw:raw-100)
        self.assertEqual(snapshot['nodes'][0]['keys'],keys)
        self.assertEqual(lookup(snapshot,2**64-1),25)
        self.assertIsNone(lookup(snapshot,26))

    def test_bitmap_leaf_uses_64_bit_groups(self):
        self.node(0x1108,43,0x2003,prefix=0x1200)
        self.word(0x2030,1<<63);self.word(0x2038,0x3005);self.word(0x3000,7)
        snapshot=decode(self.read,0x1103,lambda raw:raw)
        self.assertEqual(lookup(snapshot,0x12ff),7)
        self.assertIsNone(lookup(snapshot,0x12fe))
        self.assertIsNone(lookup(snapshot,0x13ff))

    def test_read_budget_and_short_reads_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'budget'):decode(self.read,0x1103,int,max_bytes=15)
        self.assertEqual(self.reads,[])
        with self.assertRaisesRegex(ValueError,'exactly'):decode(lambda a,n:b'',0x1103,int)
        with self.assertRaises(UnsupportedRegistryNode):decode(self.read,0x1102,int)

    def test_bad_counts_and_resolver_results(self):
        self.word(0x1100,31)
        with self.assertRaisesRegex(ValueError,'count'):decode(self.read,0x1101,int)
        self.node(0x1108,44,word=7)
        with self.assertRaisesRegex(ValueError,'logical identity'):decode(self.read,0x1103,lambda raw:None)
        self.node(0x1108,36,0x2003,prefix=255)
        with self.assertRaisesRegex(ValueError,'count'):decode(self.read,0x1103,int)

    def test_node_budget_stops_before_child_reads(self):
        self.node(0x1108,15,0x2003)
        self.memory[0x2000:0x2002]=bytes([1,0])
        with self.assertRaisesRegex(ValueError,'node budget'):decode(self.read,0x1103,int,max_nodes=1)
        self.assertEqual(self.reads,[(0x1108,16),(0x2000,8)])

    def test_unsorted_compact_keys_rejected(self):
        self.word(0x1100,1);self.word(0x1108,9);self.word(0x1110,3)
        with self.assertRaisesRegex(ValueError,'unsorted'):decode(self.read,0x1101,int)

    def test_compact_and_null_cursor_adapter(self):
        from reference.registry_snapshot import decoded_type_registry_cursor as cursor
        snapshot={'representation':'compact','keys':[0,7,2**64-1],'values':[0,1,2]}
        self.assertEqual(cursor(snapshot,0),{'key':0,'value':0})
        self.assertEqual(cursor(snapshot,0,advance=True),{'key':7,'value':1})
        self.assertEqual(cursor(snapshot,7,advance=True),{'key':2**64-1,'value':2})
        self.assertEqual(cursor(snapshot,2**64-1,advance=True),{'key':0,'value':None})
        self.assertEqual(cursor({'representation':'null'},7,advance=True),{'key':7,'value':None})


class DecodedRegistryParentTests(unittest.TestCase):
    def test_original_radix_parent_loop(self):
        import json
        from pathlib import Path
        from reference.registry_snapshot import link_decoded_type_registry
        root=Path(__file__).resolve().parents[1]/'native/snow_host'
        for name,count in [('radix_parent_branches_validation',87),('radix_parent_leaf_context_validation',24),('radix_parent_matches_validation',32)]:
            evidence=json.loads((root/(name+'.json')).read_text())
            self.assertEqual(evidence['cases'],count)
            for row in evidence['rows']:
                self.assertEqual(link_decoded_type_registry(row['snapshot'],row['parent_keys'],row['previous_parents']),row['result'])

    def test_original_compact_parent_loop_through_general_adapter(self):
        import json
        from pathlib import Path
        from reference.registry_snapshot import link_decoded_type_registry
        evidence=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/compact_parent_registry_validation.json').read_text())
        for row in evidence['rows']:
            snapshot={'representation':'compact','keys':row['registry_keys'],'values':row['descriptor_indices']} if row['registry_keys'] else {'representation':'null'}
            result=link_decoded_type_registry(snapshot,row['parent_keys'],row['previous_parents'])
            expected=row['result']
            self.assertEqual(result['parents'],expected['parents'])
            self.assertEqual(result['cursor_key'],expected['cursor_key'])
            self.assertEqual(result['visited_descriptors'],[row['descriptor_indices'][i] for i in expected['visited_slots']])
            self.assertEqual(result['visited_keys'],[row['registry_keys'][i] for i in expected['visited_slots']])

    def test_aliases_and_unregistered_descriptors(self):
        from reference.registry_snapshot import link_decoded_type_registry as link
        snapshot={'representation':'compact','keys':[0,10,20],'values':[0,1,1]}
        result=link(snapshot,[10,0,0],[None,None,1])
        self.assertEqual(result['parents'],[1,0,1])
        self.assertEqual(result['visited_descriptors'],[0,1,1])
        self.assertEqual(result['visited_keys'],[0,10,20])

    def test_budget_failure_does_not_mutate_inputs(self):
        from reference.registry_snapshot import link_decoded_type_registry as link
        old=[None,None]
        snapshot={'representation':'compact','keys':[0,10],'values':[0,1]}
        with self.assertRaisesRegex(ValueError,'budget'):link(snapshot,[10,0],old,max_entries=1)
        self.assertEqual(old,[None,None])
        with self.assertRaisesRegex(ValueError,'outside'):link({'representation':'compact','keys':[0],'values':[4]},[0], [None])

    def test_parent_key_is_not_sign_extended_or_widened(self):
        from reference.registry_snapshot import link_decoded_type_registry as link
        snapshot={'representation':'compact','keys':[2**32-1,2**64-1],'values':[0,1]}
        result=link(snapshot,[2**32-1]*2,[None,None])
        self.assertEqual(result['parents'],[0,0])
        self.assertEqual(result['cursor_key'],0)

    def test_radix_linked_parents_feed_range_preparation(self):
        from reference.registry_snapshot import link_decoded_type_registry
        from reference.ground_response_pose import prepare_type_ranges
        snapshot={'representation':'radix','root':0,'nodes':[{'kind':39,'prefix':0,'keys':[0,10,20,30],'values':[2,0,3,1]}]}
        parent_keys=[0,20,99,10]
        result=link_decoded_type_registry(snapshot,parent_keys,[None]*4)
        self.assertEqual(result['parents'],[2,3,None,0])
        prepared=prepare_type_ranges(result['parents'],[(k,32767,i) for i,k in enumerate(parent_keys)],2)
        self.assertEqual(prepared['fallback_nodes'],[])
        self.assertEqual(prepared['ranges'],[[3,8],[5,6],[2,9],[4,7]])


class TypeRegistrationDispatchTests(unittest.TestCase):
    def test_original_dynamic_dispatch(self):
        import json
        from pathlib import Path
        from reference.registry_snapshot import dispatch_type_registration_callbacks as dispatch
        evidence=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/registration_dispatch_validation.json').read_text())
        self.assertEqual(evidence['cases'],192)
        for row in evidence['rows']:
            state={'count':row['initial_count'],'array':0};calls=[]
            def invoke(entry,context):
                calls.append({'entry':entry['id'],'context':context})
                state.update(row['actions'][len(calls)-1])
            count=dispatch(lambda:state['count'],lambda i:row['entries'][state['array']][i],invoke)
            self.assertEqual(calls,row['calls'])
            self.assertEqual(state,row['final_state'])
            self.assertEqual(count,len(calls))

    def test_growth_and_array_replacement_are_observed(self):
        from reference.registry_snapshot import dispatch_type_registration_callbacks as dispatch
        state={'entries':[{'id':1,'context':7}]};calls=[]
        def invoke(entry,context):
            calls.append((entry['id'],context))
            if len(calls)==1:state['entries']=[{'id':9,'context':0},{'id':2,'context':11}]
        self.assertEqual(dispatch(lambda:len(state['entries']),lambda i:state['entries'][i],invoke),2)
        self.assertEqual(calls,[(1,4),(2,8)])

    def test_count_shrink_stops_current_pass(self):
        from reference.registry_snapshot import dispatch_type_registration_callbacks as dispatch
        state={'count':3};calls=[]
        def invoke(entry,context):calls.append(context);state['count']=0
        self.assertEqual(dispatch(lambda:state['count'],lambda i:{'context':15},invoke),1)
        self.assertEqual(calls,[12])

    def test_bounds_do_not_undo_prior_callbacks(self):
        from reference.registry_snapshot import dispatch_type_registration_callbacks as dispatch
        calls=[]
        with self.assertRaisesRegex(ValueError,'budget'):
            dispatch(lambda:2,lambda i:{'context':0},lambda entry,ctx:calls.append(ctx),max_calls=1)
        self.assertEqual(calls,[0])
        with self.assertRaisesRegex(ValueError,'uint16'):
            dispatch(lambda:65536,lambda i:None,lambda *args:None)
        with self.assertRaisesRegex(ValueError,'uint64'):
            dispatch(lambda:1,lambda i:{'context':-1},lambda *args:None)


class SlotIdentityTests(unittest.TestCase):
    def test_single_and_compact_slot_mapping(self):
        memory=bytearray(128)
        def read(a,n):return bytes(memory[a-4096:a-4096+n])
        import struct
        struct.pack_into('<QQ',memory,8,77,44<<56|5)
        seen=[]
        def slot(raw,address):seen.append((raw,address));return address
        snapshot=decode(read,4099,lambda raw:999,resolve_slot=slot)
        self.assertEqual(lookup(snapshot,5),4104)
        self.assertEqual(seen,[(77,4104)])
        struct.pack_into('<QQQ',memory,0,0,5,88)
        snapshot=decode(read,4097,int,resolve_slot=slot)
        self.assertEqual(lookup(snapshot,5),4112)
        self.assertEqual(seen[-1],(88,4112))
