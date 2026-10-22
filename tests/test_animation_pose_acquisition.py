import unittest
from reference.animation_pose_acquisition import acquire_skeleton_pose


class PoseAcquisitionTests(unittest.TestCase):
    def test_lazy_wrapper_then_eager_bank(self):
        backend=dict(resource=dict(flags=0x80000000,payload='asset'),cache='cache')
        component={'pool':'pool'}
        for eager in (0,1):
            calls=[];raw=dict(flags=0xfb,untouched='sentinel')
            def resolve(owner,payload):
                self.assertIs(owner,backend);self.assertEqual(payload,'asset')
                calls.append('resolve');return component
            result=acquire_skeleton_pose(backend,0x18001,2,eager,resolve_component=resolve,
                allocate_wrapper=lambda:raw,acquire_bank=lambda *a:(calls.append(a) or 'bank'))
            self.assertIs(result,raw);self.assertEqual(result['index'],0x8001)
            self.assertEqual(result['flags'],0xfc);self.assertEqual(result['untouched'],'sentinel')
            self.assertEqual(result['primary'],'bank' if eager else None)
            self.assertEqual(calls,['resolve',('pool',0x8001,0)] if eager else ['resolve'])

    def test_invalid_resource_does_not_resolve(self):
        backend=dict(resource=dict(flags=0,payload='asset'),cache=None)
        result=acquire_skeleton_pose(backend,65535,1,0,
            resolve_component=lambda *a:self.fail('invalid resource'),
            allocate_wrapper=lambda:dict(flags=0),acquire_bank=lambda *a:self.fail('lazy'))
        self.assertIsNone(result['component']);self.assertEqual(result['flags'],5)

    def test_failed_wrapper_allocation(self):
        backend=dict(resource=dict(flags=0,payload=None),cache=None)
        services=dict(resolve_component=lambda *a:None,allocate_wrapper=lambda:None,
                      acquire_bank=lambda *a:self.fail())
        self.assertIsNone(acquire_skeleton_pose(backend,1,0,0,**services))
        with self.assertRaises(ValueError):acquire_skeleton_pose(backend,1,0,1,**services)

    def test_instruction_receipt(self):
        import json
        from pathlib import Path
        data=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/pose_acquisition_validation.json').read_text())
        self.assertEqual(data['cases'],48)
        for row in data['rows']:
            backend=dict(resource=dict(flags=0x80000000 if row['valid_resource'] else 0,payload=55))
            events=[]
            def resolve(*a):events.extend(['lookup_key','resolve']);return {'pool':'pool'}
            def allocate():events.append('wrapper');return dict(flags=row['prior_flags'])
            def bank(pool,mask,representation):
                self.assertEqual((pool,mask,representation),('pool',row['mask']&65535,row['mode']&1))
                events.append('bank');return 'bank'
            result=acquire_skeleton_pose(backend,row['mask'],row['mode'],row['eager'],
                resolve_component=resolve,allocate_wrapper=allocate,acquire_bank=bank)
            self.assertEqual(events,row['events']);self.assertEqual(result['flags'],row['final_flags'])
