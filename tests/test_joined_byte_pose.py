import json
import struct
from pathlib import Path
import unittest
from reference.animation_pose_blend import blend_regular_byte_pose


class JoinedBytePoseTests(unittest.TestCase):
    def test_complete_instruction_path(self):
        r=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/joined_byte_pose_validation.json').read_text())
        self.assertEqual(r['cases'],24)
        for row in r['rows']:
            with self.subTest(row=row):
                def wrapper(values):
                    return dict(primary=dict(data=bytearray(struct.pack('<8f',*values)),
                        profile=r['profile'],flags=1<<26,secondary_count=0,records=[]),
                        alternate=None,component=dict(flags16=0),index=row['mask'],
                        request_byte=2 if row['prepared'] else 0)
                dst=wrapper(range(1,9));src=wrapper(range(9,17));reads=[]
                def scalar(w):reads.append(w);return row['scalar']
                def unexpected(*args):self.fail('allocation/conversion was not expected')
                visits=blend_regular_byte_pose(dst,src,row['weight'],acquire=unexpected,
                    convert=unexpected,get_owner_scalar=scalar)
                self.assertEqual(visits,row['visits'])
                for name,state in (('destination',dst),('source',src)):
                    self.assertEqual(state['primary']['data'].hex(),row[name+'_hex'])
                    self.assertEqual(state['primary']['flags'],row[name+'_flags'])
                    self.assertEqual(state['request_byte'],row['request_byte'])
                self.assertEqual(len(reads),2 if row['prepared'] else 0)
                if reads:self.assertIs(reads[0],src);self.assertIs(reads[1],dst)

    def test_instruction_path_with_alternate_conversion(self):
        r=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/joined_converted_byte_pose_validation.json').read_text())
        self.assertEqual(r['cases'],64)
        for row in r['rows']:
            with self.subTest(missing=row['missing'],ready=row['ready'],selector=row['selector']):
                models=[dict(data=bytearray(struct.pack('<16f',*v)),profile=r['profile'],
                    flags=(1<<27) if row['ready'] and i<2 else 0,secondary_count=0,
                    records=[],parent_header=bytes([i+1])*32) for i,v in enumerate(r['initial_values'])]
                def wrapper(i):return dict(primary=models[i],alternate=None if row['missing'] else models[i+2],
                    component=dict(pool='pool',flags16=row['selector']<<3),index=row['mask'],request_byte=0)
                dst,src=wrapper(0),wrapper(1);calls=[];seeds=iter(row['seeds'])
                def acquire(pool,index,mode):
                    self.assertEqual((pool,index,mode),('pool',row['mask'],0))
                    i=3 if not calls else 2;calls.append(i);return models[i]
                visits=blend_regular_byte_pose(dst,src,row['weight'],acquire=acquire,
                    get_owner_scalar=lambda w:row['scalar'],reciprocal_sqrt=lambda n:next(seeds))
                for model,expected in zip(models,row['outputs']):
                    self.assertEqual(model['data'].hex(),expected['data_hex'])
                    self.assertEqual(model['flags'],expected['flags'])
                    self.assertEqual(model['parent_header'].hex(),expected['header_hex'])
                self.assertEqual(calls,row['allocations']);self.assertEqual(visits,row['visits'])
                self.assertEqual(list(seeds),[])
                self.assertIs(dst['alternate'],models[2]);self.assertIs(src['alternate'],models[3])
                self.assertEqual(dst['request_byte'],0);self.assertEqual(src['request_byte'],0)

    def test_full_active_mask_instruction_path(self):
        r=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/joined_masked_byte_pose_validation.json').read_text())
        self.assertEqual(r['cases'],96)
        for row in r['rows']:
            def wrapper(values):return dict(primary=dict(data=bytearray(struct.pack('<8f',*values)),
                profile=r['profile'],flags=1<<26,secondary_count=0,records=[]),alternate=None,
                component=dict(flags16=0),index=row['mask'],request_byte=2 if row['prepared'] else 0)
            dst,src=wrapper(range(1,9)),wrapper(range(9,17))
            bm=dict(active_count=int(row['active']),uniform_groups=1,indices=[1],
                mode_values=[bytes([row['byte']]),b'',b''])
            def unexpected(*args):self.fail('allocation not expected')
            visits=blend_regular_byte_pose(dst,src,row['weight'],acquire=unexpected,
                get_owner_scalar=lambda w:row['scalar'],blend_mask=bm)
            self.assertEqual(visits,row['visits'])
            for state,expected in zip((dst,src),row['outputs']):
                self.assertEqual(state['primary']['data'].hex(),expected['data_hex'])
                self.assertEqual(state['primary']['flags'],expected['flags'])
                self.assertEqual(state['request_byte'],expected['request_byte'])

    def test_active_mask_with_alternate_conversion(self):
        r=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/joined_converted_masked_pose_validation.json').read_text())
        self.assertEqual(r['cases'],64)
        for row in r['rows']:
            with self.subTest(missing=row['missing'],ready=row['ready'],selector=row['selector']):
                models=[dict(data=bytearray(struct.pack('<20f',*v)),profile=r['profile'],
                    flags=(1<<27) if row['ready'] and i<2 else 0,secondary_count=0,
                    records=[],parent_header=bytes([i+1])*32) for i,v in enumerate(r['initial_values'])]
                def wrapper(i):return dict(primary=models[i],alternate=None if row['missing'] else models[i+2],
                    component=dict(pool='pool',flags16=row['selector']<<3),index=row['mask'],request_byte=0)
                dst,src=wrapper(0),wrapper(1);calls=[];seeds=iter(row['seeds'])
                def acquire(pool,index,mode):
                    self.assertEqual((pool,index,mode),('pool',row['mask'],0))
                    i=3 if not calls else 2;calls.append(i);return models[i]
                visits=blend_regular_byte_pose(dst,src,row['weight'],acquire=acquire,
                    get_owner_scalar=lambda w:row['scalar'],reciprocal_sqrt=lambda n:next(seeds),
                    blend_mask=dict(active_count=1,uniform_groups=0,indices=[1],mode_values=[bytes([127]),b'',b'']))
                for model,expected in zip(models,row['outputs']):
                    self.assertEqual(model['data'].hex(),expected['data_hex'])
                    self.assertEqual(model['flags'],expected['flags'])
                    self.assertEqual(model['parent_header'].hex(),expected['header_hex'])
                self.assertEqual(calls,row['allocations']);self.assertEqual(visits,row['visits'])
                self.assertEqual(list(seeds),[])
                self.assertIs(dst['alternate'],models[2]);self.assertIs(src['alternate'],models[3])
                self.assertEqual(dst['request_byte'],0);self.assertEqual(src['request_byte'],0)
