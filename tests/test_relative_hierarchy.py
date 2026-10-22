"""Synthetic contract checks and replay of original-instruction observations."""
import json
import math
from pathlib import Path
import struct
import unittest
from reference.animation_hierarchy import decompose_bank_hierarchy


def packed(records):
    return b''.join(struct.pack('<8f', *(list(p)+list(q))) for p,q in records)


class RelativeHierarchyTests(unittest.TestCase):
    def test_original_instruction_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/relative_hierarchy_validation.json').read_text())
        self.assertEqual(receipt['cases'],192)
        for index,sample in enumerate(receipt['samples']):
            with self.subTest(case=index):
                seeds=iter(sample['rsqrt_seeds'])
                actual=decompose_bank_hierarchy(**sample['inputs'],
                    reciprocal_sqrt=lambda _:next(seeds))
                expected=sample['result']
                self.assertEqual(packed(actual['records']),packed(expected['records']))
                for key in ('visited','skipped','in_place'):
                    self.assertEqual(actual[key],expected[key])
                self.assertEqual(list(seeds),[])

    def test_alias_reads_already_converted_parent(self):
        source=[([x,0.,0.,0.],[0.,0.,0.,1.]) for x in (2.,5.,9.)]
        metadata=[dict(parent=max(0,i-1),rank=0,skip_span=0) for i in range(3)]
        kwargs=dict(metadata=metadata,mask=0,reciprocal_sqrt=lambda n:1/math.sqrt(n))
        separate=decompose_bank_hierarchy(source,list(source),**kwargs)
        inplace=decompose_bank_hierarchy(source,None,**kwargs)
        explicit=decompose_bank_hierarchy(source,source,**kwargs)
        self.assertEqual(separate['records'][2][0][0],4.)
        self.assertEqual(inplace['records'][2][0][0],6.)
        self.assertEqual(packed(explicit['records']),packed(inplace['records']))
        self.assertEqual(source[1][0][0],5.)  # inspection API does not mutate caller

    def test_skip_preserves_destination_and_root_ignores_rank(self):
        source=[([x,0.,0.,0.],[0.,0.,0.,1.]) for x in (2.,5.,9.)]
        dest=[([100.,0.,0.,0.],[0.,0.,0.,1.]) for _ in source]
        metadata=[dict(parent=0,rank=7,skip_span=1) for _ in source]
        result=decompose_bank_hierarchy(source,dest,metadata,0,lambda n:1/math.sqrt(n))
        self.assertEqual(result['visited'],[0])
        self.assertEqual(result['skipped'],[[1,3]])
        self.assertEqual(packed(result['records'][1:]),packed(dest[1:]))

    def test_empty_does_not_request_normalization(self):
        def unexpected(_):
            self.fail('empty bank requested normalization')
        self.assertEqual(decompose_bank_hierarchy([],None,[],0,unexpected)['records'],[])

    def test_joined_selector_converter_receipt(self):
        self.replay_selection_receipt(False)

    def test_selection_conversion_scaling_receipt(self):
        self.replay_selection_receipt(True)

    def replay_selection_receipt(self, scaled):
        from reference.skeleton_parent_transform import select_converted_owner_bank, select_owner_scaled_bank
        from reference.animation_hierarchy import convert_relative_pose_bank
        import copy
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            ('native/snow_host/scaled_relative_selection_validation.json' if scaled else
             'native/snow_host/joined_relative_selection_validation.json')).read_text())
        self.assertEqual(receipt['cases'],192)
        for index,row in enumerate(receipt['rows']):
            with self.subTest(case=index):
                banks=copy.deepcopy(row['banks'])
                for bank in banks.values():bank['parent_header']=bytes(bank['parent_header'])
                state=dict(primary=banks['primary'],alternate=banks['alternate'] if row['alternate_present'] else None,
                    index=37,request_byte=row['request_byte'],component=dict(pool='pool',flags16=row['mode']<<3))
                events=[];seeds=iter(row['rsqrt_seeds'])
                def acquire(pool,index,request):
                    self.assertEqual(pool,'pool');events.append(['acquire',index,request]);return banks['new']
                def convert(source,destination,mode):
                    events.append(['convert',source['name'],destination['name'],mode])
                    convert_relative_pose_bank(source,destination,mode,lambda _:next(seeds))
                if scaled:
                    def sync_arrays(bank):
                        bank['primary_records']=[list(p)+list(q) for p,q in bank['records']]
                        bank['primary_count']=len(bank['records'])
                        bank['secondary_records']=[];bank['secondary_count']=0
                    for bank in banks.values():sync_arrays(bank)
                    original_convert=convert
                    def convert(source,destination,mode):
                        original_convert(source,destination,mode);sync_arrays(destination)
                    result=select_owner_scaled_bank(state,acquire=acquire,convert=convert,
                        get_owner_scalar=lambda:row['scale'])
                    for bank in banks.values():
                        bank['records']=[(r[:4],r[4:]) for r in bank['primary_records']]
                else:
                    result=select_converted_owner_bank(state,acquire=acquire,convert=convert)
                self.assertEqual(result['name'],row['returned_bank'])
                self.assertEqual(state['request_byte'],row['wrapper_flags'])
                self.assertEqual(state['alternate']['name'] if state['alternate'] else None,row['alternate_bank'])
                self.assertEqual(events,row['events']);self.assertEqual(list(seeds),[])
                for name,bank in banks.items():
                    expected=row['result_banks'][name]
                    self.assertEqual(packed(bank['records']),packed(expected['records']))
                    self.assertEqual(list(bank['parent_header']),expected['parent_header'])
                    self.assertEqual(bank['flags'],expected['flags'])
                    self.assertEqual(bank['metadata'],expected['metadata'])
