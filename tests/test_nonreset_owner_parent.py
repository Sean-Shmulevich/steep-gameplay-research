import json
from pathlib import Path
import unittest
from reference.skeleton_parent_transform import publish_nonreset_owner_parent, select_and_publish_owner_parent
from reference.skeleton_parent_transform import query_remapped_parent_bank
from reference.skeleton_parent_transform import publish_pose_work_result
from reference.skeleton_parent_transform import initialize_pose_work_descriptors
from reference.skeleton_parent_transform import prepare_owner_scaled_bank
from reference.skeleton_parent_transform import remove_owner_bank_scale
from reference.skeleton_parent_transform import select_converted_owner_bank


class NonresetOwnerParentTests(unittest.TestCase):
    def test_opposite_selector_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/opposite_bank_selection_validation.json').read_text())
        for row in receipt['rows']:
            banks={name:dict(name=name,flags=f) for name,f in (
                ('primary',(row['primary_bit26']<<26)|(row['primary_bit27']<<27)|0x123),
                ('alternate',(row['alternate_bit27']<<27)|0x456),('new',(1<<26)|0x789))}
            state=dict(primary=banks['primary'],alternate=banks['alternate'] if row['alternate_present'] else None,
                index=37,request_byte=0xa0|row['request_low_bit'],component=dict(pool='pool',flags16=40))
            events=[]
            def acquire(p,i,r):
                self.assertEqual(p,'pool');events.append(['acquire',i,r]);return banks['new']
            def convert(s,d,m):
                events.append(['convert',s['name'],d['name'],m])
                if row['convert_mutates_flags']:
                    state['request_byte']=0xf1;s['flags']=d['flags']=0xabcdef12
            result=select_converted_owner_bank(state,acquire=acquire,convert=convert)
            self.assertEqual(events,row['events']);self.assertEqual(result['name'],row['returned_bank'])
            self.assertEqual({k:b['flags'] for k,b in banks.items()},row['flags'])
            self.assertEqual(state['request_byte'],row['wrapper_flags'])

    def test_reciprocal_and_roundtrip_receipts(self):
        for filename,joined in (('owner_bank_unscale_validation.json',False),
                                ('owner_bank_scale_roundtrip_validation.json',True)):
            receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host'/filename).read_text())
            for row in receipt['rows']:
                a=[[float(i*8+j+1) for j in range(8)] for i in range(4)]
                b=[[float(-i*8-j-1) for j in range(8)] for i in range(4)]
                bank=dict(primary_records=a,primary_count=row['primary_count'],
                          secondary_records=a if row['alias'] else b,secondary_count=row['secondary_count'])
                state=dict(request_byte=0xa1|int(row['already_prepared'])*2)
                if joined:prepare_owner_scaled_bank(state,bank,lambda:row['scale'])
                self.assertIs(remove_owner_bank_scale(state,bank,lambda:row['scale']),bank)
                self.assertEqual(a,row['expected_primary']);self.assertEqual(b,row['expected_secondary'])
                self.assertEqual(state['request_byte'],row['expected_flags'])

    def test_removal_reads_new_scalar_and_unprepared_skips_getter(self):
        bank=dict(primary_records=[[1.,2.,3.,1.,0.,0.,0.,1.]],primary_count=1,
                  secondary_records=[],secondary_count=0)
        state={'request_byte':0}
        def forbidden():raise AssertionError('unprepared removal must not read scalar')
        remove_owner_bank_scale(state,bank,forbidden)
        prepare_owner_scaled_bank(state,bank,lambda:2.)
        remove_owner_bank_scale(state,bank,lambda:4.)
        self.assertEqual(bank['primary_records'][0][:4],[.5,1.,1.5,.5])
        self.assertEqual(state['request_byte'],0)

    def test_owner_scale_instruction_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/owner_bank_scale_validation.json').read_text())
        for row in receipt['rows']:
            a=[[float(i*8+j+1) for j in range(8)] for i in range(4)]
            b=[[float(-i*8-j-1) for j in range(8)] for i in range(4)]
            bank=dict(primary_records=a,primary_count=row['primary_count'],
                      secondary_records=a if row['alias'] else b,secondary_count=row['secondary_count'])
            state=dict(request_byte=0xa1|int(row['already_prepared'])*2)
            def scalar():
                self.assertFalse(row['already_prepared'])
                return row['scale']
            self.assertIs(prepare_owner_scaled_bank(state,bank,scalar),bank)
            self.assertEqual(a,row['expected_primary']);self.assertEqual(b,row['expected_secondary'])
            self.assertEqual(state['request_byte'],row['expected_flags'])

    def test_wrapper_initialization_preserves_high_flag_bits(self):
        component=object();current=object()
        for seed in range(256):
            r=initialize_pose_work_descriptors(component,current,seed,255-seed)
            self.assertIs(r['input']['component'],component)
            self.assertIs(r['input']['primary'],current)
            self.assertIsNone(r['output']['primary'])
            self.assertEqual(r['input']['flags'],seed & 248)
            self.assertEqual(r['output']['flags'],(255-seed) & 248)
            for d in r.values():
                self.assertEqual((d['header'],d['index']),(32772,65535))
                self.assertIsNone(d['alternate'])
                self.assertEqual(d['storage'],'own_inline_scratch')
                self.assertNotIn('scratch_contents',d)

    def test_wrapper_initialization_rejects_invalid_prior_flags(self):
        for flags in (-1,256,True,1.5):
            with self.assertRaises(ValueError):
                initialize_pose_work_descriptors(None,None,flags,0)

    def test_work_publication_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/pose_work_publication_validation.json').read_text())
        for row in receipt['rows']:
            state={'primary':'old_primary','current':'new_current'}
            events=[['work',row['work_flag']]]
            def select(w):events.append(['select']);return 'selected'
            def copy_selected(d,s,m,i):
                events.append(['copy_selected',d,s,m,i])
                if row['replace_primary_during_copy']:state['primary']='new_primary'
            def copy_primary(d,s,m):events.append(['copy_primary',d,s,m])
            publish_pose_work_result(state,{},'captured_current',row['mode'],
                succeeded=row['success'],select_bank=select,copy_selected=copy_selected,
                copy_primary=copy_primary)
            self.assertEqual(events,row['events'])

    def test_query_gates_and_order(self):
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/remapped_parent_query_validation.json').read_text())
        defaults=receipt['rows'][0]['output']
        for row in receipt['rows']:
            events=[]
            state={}
            def select(s):
                events.append(['select']);s['published']=True;return 'bank'
            def read(bank,index):
                self.assertTrue(state['published']);self.assertEqual(bank,'bank')
                events.append(['read',index]);return [[2.,3.,4.,5.],[6.,7.,8.,9.]]
            result=query_remapped_parent_bank([row['mapped_index']]*3,row['index'],state,
                select_bank=select,read_pose=read,default_pair=defaults)
            self.assertEqual(result,row['output']);self.assertEqual(events,row['events'])
            self.assertEqual(bool(state),bool(events))

    def test_selection_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/owner_parent_selection_validation.json').read_text())
        for row in receipt['rows']:
            banks = {name:dict(name=name, flags=flags) for name,flags in (
                ('primary',(row['primary_bit26']<<26)|(row['primary_bit27']<<27)|0x123),
                ('alternate',(row['alternate_bit27']<<27)|0x456),('new',(1<<26)|0x789))}
            state = dict(primary=banks['primary'],
                         alternate=banks['alternate'] if row['alternate_present'] else None,
                         request_byte=0xa0|row['request_low_bit'],component=dict(pool='pool',flags16=16))
            events=[]
            def acquire(pool,index,bit):
                self.assertEqual((pool,index),('pool',0xffff))
                events.append(['acquire',bit]);return banks['new']
            def prepare(s,b):
                events.append(['prepare',b['name']])
                if row['prepare_changes_mode']:s['component']['flags16']=56
            def parent(b,p,reset):events.append(['parent',b['name'],int(reset)])
            def process(d,s,mode):events.append(['process',d['name'],s['name'],mode])
            result=select_and_publish_owner_parent(state,acquire=acquire,prepare=prepare,
                resolve_owner=lambda c:([[1,0,0,0],[0,1,0,0],[0,0,1,0]],[2,3,4,99]),
                set_parent=parent,process=process)
            self.assertEqual(result['name'],row['returned_bank'])
            self.assertEqual(events,row['events'])

    def test_original_instruction_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/nonreset_owner_parent_validation.json').read_text())
        self.assertEqual(receipt['cases'], 32)
        for row in receipt['rows']:
            calls = []
            prepared = publish_nonreset_owner_parent(**row['inputs'], bank='bank',
                set_parent=lambda *args: calls.append(args))
            self.assertEqual(json.loads(json.dumps(prepared)), row['prepared'])
            self.assertEqual(calls, [('bank', prepared, False)])
            self.assertEqual(prepared['parent_position'][3], 1)
            self.assertTrue(row['remainder_unchanged'])

    def test_service_failure_propagates(self):
        def refused(*args):
            raise RuntimeError('destination lifetime unavailable')
        with self.assertRaisesRegex(RuntimeError, 'lifetime'):
            publish_nonreset_owner_parent([[1,0,0,0],[0,1,0,0],[0,0,1,0]],
                                         [1,2,3,17], object(), refused)
