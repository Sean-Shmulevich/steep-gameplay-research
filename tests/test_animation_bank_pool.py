import copy
import json
from pathlib import Path
import unittest
from reference.animation_bank_pool import reuse_pose_bank


class PoolReuseTests(unittest.TestCase):
    def test_instruction_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/pool_reuse_validation.json').read_text())
        self.assertEqual(receipt['cases'],96)
        for row in receipt['rows']:
            entries=copy.deepcopy(row['entries']);calls=[]
            result=reuse_pose_bank(entries,row['request_mask'],row['representation'],row['mode'],
                'source',lambda dst,src,mode,mask:calls.append([mode,mask]))
            self.assertIs(result,entries[1]['bank'])
            self.assertEqual(entries,row['result_entries'])
            self.assertEqual(calls,row['copy_calls'])

    def test_miss_is_explicit_and_does_not_allocate(self):
        entries=[dict(occupied_mask=1,initialized_mask=7,representation_word=0,bank=dict(flags=42))]
        before=copy.deepcopy(entries)
        self.assertIsNone(reuse_pose_bank(entries,1,0,0,None,lambda *args:self.fail('copy on miss')))
        self.assertEqual(entries,before)

    def test_first_compatible_entry_wins(self):
        entries=[dict(occupied_mask=0,initialized_mask=0,representation_word=0,bank=dict(flags=i)) for i in (11,22)]
        self.assertIs(reuse_pose_bank(entries,2,0,0,None,lambda *args:self.fail('copy unnecessary')),entries[0]['bank'])
        self.assertEqual(entries[1]['occupied_mask'],0)

    def test_copy_flag_mutation_survives_except_readiness(self):
        entries=[dict(occupied_mask=0,initialized_mask=1,representation_word=0,bank=dict(flags=0))]
        def copy_selected(dst,src,mode,mask):dst['flags']=0xffffffff
        result=reuse_pose_bank(entries,1,0,0,None,copy_selected)
        self.assertEqual(result['flags'],0xffffffff & ~(1<<27))

    def test_release_instruction_receipt(self):
        from reference.animation_bank_pool import release_pose_bank
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/pool_release_validation.json').read_text())
        self.assertEqual(receipt['cases'],120)
        for row in receipt['rows']:
            bank=copy.deepcopy(row['initial_bank']);calls=[]
            entry=dict(occupied_mask=0xffff,initialized_mask=0xabcd,representation_word=0xa1,bank=bank)
            found=release_pose_bank([entry],bank if row['found'] else {},row['request_mask'],lambda _:calls.append('clear'))
            self.assertEqual(found,row['found']);self.assertEqual(bank,row['result_bank'])
            self.assertEqual(entry['occupied_mask'],row['occupied_mask'])
            self.assertEqual(entry['initialized_mask'],0xabcd)
            self.assertEqual(entry['representation_word'],0xa1)
            self.assertEqual(calls,row['clear_calls'])

    def test_release_then_reuse_keeps_bank_identity(self):
        from reference.animation_bank_pool import release_pose_bank
        bank=dict(flags=0,auxiliary_mask=0,auxiliary_count=0)
        entry=dict(occupied_mask=0x8001,initialized_mask=1,representation_word=0,bank=bank)
        self.assertIsNone(reuse_pose_bank([entry],1,0,0,None,lambda *a:None))
        self.assertTrue(release_pose_bank([entry],bank,1,lambda *a:self.fail('unexpected clear')))
        self.assertEqual(entry['occupied_mask'],0x8000)
        calls=[]
        self.assertIs(reuse_pose_bank([entry],1,0,0,'source',lambda *a:calls.append(a)),bank)
        self.assertEqual(len(calls),1)
        self.assertEqual(entry['occupied_mask'],0x8001)

    def test_joined_work_cleanup_receipt(self):
        from reference.animation_bank_pool import cleanup_pose_work_wrappers,release_pose_bank
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/work_cleanup_validation.json').read_text())
        self.assertEqual(receipt['cases'],128)
        for row in receipt['rows']:
            banks=copy.deepcopy(row['banks']);events=[]
            entries=[dict(occupied_mask=65535,initialized_mask=65535,representation_word=0,bank=b) for b in banks]
            wrappers=[]
            for w in row['wrappers']:
                wrappers.append(dict(w,component=dict(pool='pool'),primary=banks[w['primary']] if w['primary'] is not None else None,
                    alternate=banks[w['alternate']] if w['alternate'] is not None else None))
            def release(pool,bank,mask):
                self.assertEqual(pool,'pool')
                events.append(['release',next(i for i,b in enumerate(banks) if b is bank),mask])
                release_pose_bank(entries,bank,mask,lambda _:self.fail('unexpected auxiliary clear'))
            def free(storage):events.extend([['storage_lookup',storage],['free_storage',storage]])
            cleanup_pose_work_wrappers(*wrappers,release,free)
            self.assertEqual(events,row['events']);self.assertEqual(banks,row['result_banks'])
            self.assertEqual([e['occupied_mask'] for e in entries],row['occupied_masks'])
            self.assertEqual([w['flags'] for w in wrappers],row['wrapper_flags'])
            for i,w in enumerate(wrappers):
                self.assertIsNone(w['primary']);self.assertIsNone(w['alternate'])
                self.assertEqual(w['storage'],row['wrappers'][i]['storage'])

    def test_pool_reuse_with_actual_copy_receipt(self):
        from reference.animation_bank_copy import copy_pose_bank
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/pool_reuse_copy_validation.json').read_text())
        self.assertEqual(receipt['cases'],96)
        for row in receipt['rows']:
            entries=copy.deepcopy(row['entries']);calls=[]
            words=[1]*32;words[0]=0;words[7]=3
            entries[1]['bank'].update(parent_header=bytes([231])*32,data=bytearray([194]*128),
                group_words=words,descriptors=[dict(offset=i*16,kind=i%7) for i in range(7)])
            source=dict(parent_header=bytes(range(32)),data=bytes(range(128)),group_count=2,bulk_boundaries=[32,48,85])
            def copy_selected(dst,src,mode,mask):calls.append([mode,mask]);copy_pose_bank(dst,src,mode,mask)
            result=reuse_pose_bank(entries,row['request_mask'],row['representation'],row['mode'],source,copy_selected)
            self.assertEqual(list(result.pop('data')),row['expected_data'])
            self.assertEqual(list(result.pop('parent_header')),row['expected_header'])
            result.pop('group_words');result.pop('descriptors')
            self.assertEqual(entries,row['result_entries']);self.assertEqual(calls,row['copy_calls'])

    def test_new_entry_initialization_receipt(self):
        from reference.animation_bank_pool import initialize_pool_entry
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/pool_entry_init_validation.json').read_text())
        self.assertEqual(receipt['cases'],60)
        for row in receipt['rows']:
            actual=initialize_pool_entry(bytes(row['raw_slot']),row['request_mask'],row['representation'])
            self.assertEqual(list(actual),row['expected_slot'])
            self.assertEqual(actual[6:8],bytes(row['raw_slot'][6:8]))
            self.assertEqual(actual[8:],bytes(8))

    def test_constructor_instruction_receipt(self):
        from reference.animation_bank_pool import construct_pose_bank_fields
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/bank_constructor_validation.json').read_text())
        self.assertEqual(receipt['cases'],96)
        for row in receipt['rows']:
            result=construct_pose_bank_fields(row['prior_flags'],bytes(row['default_transform']))
            result['secondary_transform']=list(result['secondary_transform'])
            self.assertEqual(result,row['result'])
            self.assertNotIn('parent_header',result)
            self.assertEqual(result['secondary_storage'],'own_inline_storage')

    def test_post_constructor_seeding_receipt(self):
        from reference.animation_bank_pool import seed_new_pose_bank
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/bank_seeding_validation.json').read_text())
        self.assertEqual(receipt['cases'],24)
        for row in receipt['rows']:
            bank=dict(flags=row['initial_flags'],secondary_count=0);calls=[]
            profile=dict(total_size=row['total_size'])
            source=dict(parent_header=bytes([99])*32,data=bytes(row['source_data']),bulk_boundaries=row['boundaries'])
            def allocate(size):calls.append(size);return bytearray(size)
            seed_new_pose_bank(bank,profile,source,bytes(row['default_transform']),row['mode'],allocate)
            self.assertEqual(calls,[row['total_size']]);self.assertIs(bank['profile'],profile)
            self.assertEqual(bank['flags'],row['expected_flags']);self.assertEqual(list(bank['data']),row['expected_data'])
            self.assertEqual(list(bank['parent_header']),row['default_transform'])
            self.assertEqual(bank['parent_header'],bank['secondary_transform'])

    def test_complete_successful_miss_composition(self):
        from reference.animation_bank_pool import initialize_pool_entry,construct_pose_bank_fields,seed_new_pose_bank
        root=Path(__file__).resolve().parents[1]/'native/snow_host'
        receipt=json.loads((root/'pool_miss_join_validation.json').read_text())
        relocation=json.loads((root/'pool_relocation_validation.json').read_text())
        self.assertEqual(receipt['cases'],40);self.assertEqual(relocation['cases'],40)
        for row in receipt['rows']+relocation['rows']:
            slot=initialize_pool_entry(bytes(row['raw_slot']),row['request_mask'],row['representation'])
            self.assertEqual(list(slot[:8]),row['expected_slot_prefix'])
            transform=bytes(row['default_transform'])
            bank=construct_pose_bank_fields(row['prior_flags'],transform)
            source=dict(parent_header=bytes([99])*32,data=bytes(row['source_data']),bulk_boundaries=[32,48,85])
            calls=[]
            def allocate(size):calls.append(size);return bytearray(size)
            copied=seed_new_pose_bank(bank,dict(total_size=85),source,transform,3,allocate)
            self.assertEqual(copied['path'],'full');self.assertEqual(calls,[85])
            self.assertEqual(bank['flags'],row['expected_flags'])
            self.assertEqual(list(bank['data']),row['source_data'])
            self.assertEqual(bank['parent_header'],transform)
            self.assertEqual(row['events'][-1],['copy',65535])
