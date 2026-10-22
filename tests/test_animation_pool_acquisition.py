import json
from pathlib import Path
import struct
import unittest
from reference.animation_bank_pool import acquire_pose_bank
from reference.animation_bank_copy import copy_pose_bank


class AcquisitionTests(unittest.TestCase):
    def services(self):
        return dict(profile=dict(total_size=85),default_transform=bytes(32),reserve_slot=lambda n:bytes(16),
            allocate_bank=lambda size,alignment:dict(flags=0),allocate_data=lambda size:bytearray(size),copy_selected=copy_pose_bank)

    def source(self):
        return dict(parent_header=bytes([99])*32,data=bytes(range(85)),bulk_boundaries=[32,48,85])

    def test_joined_miss_receipts_through_api(self):
        root=Path(__file__).resolve().parents[1]/'native/snow_host'
        for name in ('pool_miss_join_validation.json','pool_relocation_validation.json'):
            for row in json.loads((root/name).read_text())['rows']:
                entries=[dict(occupied_mask=0,initialized_mask=0,representation_word=1-row['representation'],bank=dict(flags=0)) for _ in range(row['old_count'])]
                calls=[];services=self.services()
                def reserve(count):calls.append(['reserve',count]);return bytes(row['raw_slot'])
                def allocate(size,alignment):
                    self.assertIsNone(entries[-1]['bank'])
                    self.assertEqual((size,alignment),(448,16));return dict(flags=row['prior_flags'])
                def allocate_data(size):
                    self.assertIsNotNone(entries[-1]['bank'])
                    return bytearray(size)
                services.update(reserve_slot=reserve,allocate_bank=allocate,allocate_data=allocate_data,
                    default_transform=bytes(row['default_transform']))
                source=self.source();source['data']=bytes(row['source_data'])
                result=acquire_pose_bank(entries,row['request_mask'],row['representation'],3,source,**services)
                self.assertTrue(result['created']);self.assertIs(result['bank'],entries[-1]['bank'])
                self.assertEqual(result['bank']['flags'],row['expected_flags'])
                self.assertEqual(bytes(result['bank']['data']),source['data'])
                entry=entries[-1]
                prefix=struct.pack('<HHH',entry['occupied_mask'],entry['initialized_mask'],entry['representation_word'])+entry['reserved_bytes']
                self.assertEqual(list(prefix),row['expected_slot_prefix'])
                self.assertEqual(calls,[['reserve',row['old_count']+1]])

    def test_failure_leaves_explicit_partial_publication(self):
        entries=[];services=self.services();services['allocate_data']=lambda size:None
        with self.assertRaises(ValueError):acquire_pose_bank(entries,1,0,0,self.source(),**services)
        self.assertEqual(len(entries),1);self.assertIsNotNone(entries[0]['bank'])
        self.assertIs(entries[0]['bank']['profile'],services['profile'])
        self.assertIsNone(entries[0]['bank']['data'])

    def test_null_bank_does_not_claim_success(self):
        entries=[];services=self.services();services['allocate_bank']=lambda *args:None
        with self.assertRaises(ValueError):acquire_pose_bank(entries,1,0,0,self.source(),**services)
        self.assertEqual(len(entries),1);self.assertIsNone(entries[0]['bank'])

    def test_demo_allocates_once_then_reuses(self):
        from engine.examples.animation_pool_allocation_demo import run
        result=run();self.assertTrue(result['same_bank']);self.assertTrue(result['data_matches'])
        self.assertTrue(result['created_first']);self.assertFalse(result['created_second'])
        self.assertEqual(result['pool_count'],1)
        self.assertEqual(sum(e[0]=='allocate_bank' for e in result['events']),1)

    def test_constructed_bank_can_be_reused_for_partial_copy(self):
        from reference.animation_bank_pool import release_pose_bank
        entries=[];services=self.services()
        profile=dict(total_size=85,bulk_boundaries=[32,48,85],group_count=1,
            group_words=[0,1,1,1,1,1,1,1,1],descriptors=[dict(offset=16,kind=4)])
        services['profile']=profile
        source=dict(parent_header=bytes([99])*32,data=bytes(range(85)),profile=profile)
        first=acquire_pose_bank(entries,1,0,0,source,**services);bank=first['bank']
        release_pose_bank(entries,bank,1,lambda _:None)
        source['data']=bytes([213])*85
        second=acquire_pose_bank(entries,1,0,0,source,**services)
        self.assertFalse(second['created']);self.assertIs(second['bank'],bank)
        self.assertEqual(bytes(bank['data']),bytes(range(16))+bytes([213])*12+bytes(range(28,85)))
        self.assertEqual(bank['parent_header'],bytes(32))
        # The constructed bank must also be usable as a source via its profile.
        destination=dict(flags=0,parent_header=bytes(32),data=bytearray(85))
        copy_pose_bank(destination,bank,0,65535)
        self.assertEqual(destination['data'],bank['data'])
