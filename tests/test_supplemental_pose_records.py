import json
from pathlib import Path
import unittest
from reference.supplemental_pose_records import update_equal_supplemental_records as update


class SupplementalRecordTests(unittest.TestCase):
    def test_original_tail_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/supplemental_equal_validation.json').read_text())
        self.assertEqual(receipt['cases'], 36)
        for sample in receipt['samples']:
            calls = []
            def rotate(a,b,w):
                calls.append([a,b,w]); return [11,12,13,14]
            self.assertEqual(update(**sample['inputs'],rotate=rotate),sample['result'])
            self.assertEqual(calls,sample['rotation_calls'])

    def test_unreconstructed_branch_and_counter_boundary_refused(self):
        with self.assertRaises(ValueError): update([], [{}], [], .5, None)
        with self.assertRaises(ValueError): update([{}]*256, [{}]*256, [], .5, None)

    def test_rotation_dispatch_receipt(self):
        from reference.supplemental_pose_records import blend_supplemental_rotation
        import struct
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/supplemental_rotation_validation.json').read_text())
        self.assertEqual(receipt['cases'], 69)
        for sample in receipt['samples']:
            calls = []
            def fallback(a,b,w):
                calls.append([list(a),list(b),w]); return [11,12,13,14]
            def seed(n):
                self.assertEqual(n,sample['lengths'][0]); return sample['seeds'][0]
            result = blend_supplemental_rotation(**sample['inputs'],
                reciprocal_sqrt=seed,fallback=fallback)
            self.assertEqual(result['branch'],sample['result']['branch'])
            self.assertEqual(struct.pack('<4f',*result['rotation']),
                             struct.pack('<4f',*sample['result']['rotation']))
            self.assertEqual(calls,sample['fallback_calls'])

    def test_authored_zero_length_refusal(self):
        from reference.supplemental_pose_records import blend_supplemental_rotation
        with self.assertRaises(ValueError):
            blend_supplemental_rotation([0,0,0,1],[0,0,0,2],-1,None,None)

    def test_polynomial_helper_receipt(self):
        from reference.supplemental_pose_records import polynomial_rotation_blend
        import struct
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/polynomial_rotation_validation.json').read_text())
        self.assertEqual(receipt['cases'], 160)
        for sample in receipt['samples']:
            def seed(n):
                self.assertEqual(n,sample['length']); return sample['seed']
            result = polynomial_rotation_blend(**sample['inputs'],reciprocal_sqrt=seed)
            self.assertEqual(struct.pack('<4f',*result),struct.pack('<4f',*sample['result']))

    def test_joined_record_evaluation(self):
        from reference.supplemental_pose_records import evaluate_equal_supplemental_records
        import struct
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/supplemental_joined_validation.json').read_text())
        self.assertEqual(receipt['cases'],36)
        for sample in receipt['samples']:
            used=[]
            def seed(n):
                index=len(used); used.append(n)
                self.assertEqual(n,sample['lengths'][index]); return sample['seeds'][index]
            output=evaluate_equal_supplemental_records(**sample['inputs'],reciprocal_sqrt=seed)
            self.assertEqual(len(used),len(sample['seeds']))
            for actual,expected in zip(output,sample['result']):
                self.assertEqual(actual['id'],expected['id'])
                for field in ('vector','rotation'):
                    self.assertEqual(struct.pack('<4f',*actual[field]),
                                     struct.pack('<4f',*expected[field]))

    def test_unequal_record_evaluation(self):
        from reference.supplemental_pose_records import evaluate_supplemental_records
        import struct
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/supplemental_unequal_validation.json').read_text())
        self.assertEqual(receipt['cases'],48)
        for sample in receipt['samples']:
            used=[]
            def seed(n):
                index=len(used);used.append(n)
                self.assertEqual(n,sample['lengths'][index]);return sample['seeds'][index]
            output=evaluate_supplemental_records(**sample['inputs'],reciprocal_sqrt=seed)
            self.assertEqual(len(used),len(sample['seeds']))
            for actual,expected in zip(output,sample['result']):
                self.assertEqual(actual['id'],expected['id'])
                for field in ('vector','rotation'):
                    self.assertEqual(struct.pack('<4f',*actual[field]),
                                     struct.pack('<4f',*expected[field]))

    def test_short_first_list_leaves_destination_tail(self):
        from reference.supplemental_pose_records import evaluate_supplemental_records
        first=[dict(id=1,vector=[2]*4,rotation=[0,0,0,1])]
        second=first*3
        destination=[dict(id=9,vector=[99]*4,rotation=[0,0,0,1]) for _ in range(3)]
        output=evaluate_supplemental_records(first,second,destination,.5,None)
        self.assertEqual(output[0]['vector'],[1]*4)
        self.assertEqual(output[1:],destination[1:])
        self.assertEqual(output[0]['id'],9)
        self.assertEqual(destination[0]['vector'],[99]*4)

    def test_copy_gate_receipt(self):
        from reference.supplemental_pose_records import plan_supplemental_copy
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/supplemental_copy_gate_validation.json').read_text())
        self.assertEqual(receipt['cases'],162)
        for sample in receipt['samples']:
            plan=plan_supplemental_copy(**sample['inputs'])
            self.assertEqual([plan['source']] if plan['copy'] else [],sample['copies'])

    def test_empty_selected_source_does_not_fall_back(self):
        from reference.supplemental_pose_records import plan_supplemental_copy
        plan=plan_supplemental_copy(2,.5,65535,0,4,65535,65535)
        self.assertEqual(plan,dict(source='first',copy=False,reason='empty'))

    def test_original_copy_storage_with_overlap(self):
        from reference.supplemental_pose_records import copy_supplemental_storage
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/supplemental_copy_storage_validation.json').read_text())
        self.assertEqual(receipt['cases'],32)
        for sample in receipt['samples']:
            result=copy_supplemental_storage(bytes.fromhex(sample['storage']),
                sample['source_base'],sample['destination_base'],sample['count'],sample['capacity'])
            self.assertEqual(result['storage'].hex(),sample['result'])
            self.assertEqual(result['count'],sample['count'])

    def test_forward_overlap_is_not_snapshot_copy(self):
        from reference.supplemental_pose_records import copy_supplemental_storage as copy
        storage=b'A'*16+b'B'*16+b'C'*16+b'D'*16
        result=copy(storage,0,16,1,1)
        self.assertEqual(result['storage'],b'A'*64)
        with self.assertRaises(ValueError): copy(storage,0,16,1,0)

    def test_reserve_ownership_receipt(self):
        from reference.supplemental_pose_records import plan_supplemental_reserve
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/supplemental_reserve_validation.json').read_text())
        self.assertEqual(receipt['cases'],64)
        for sample in receipt['samples']:
            self.assertEqual(plan_supplemental_reserve(**sample['inputs']),sample['result'])

    def test_reserve_release_gate_and_noop(self):
        from reference.supplemental_pose_records import plan_supplemental_reserve as plan
        self.assertFalse(plan(0x8004,8)['release_old'])
        self.assertTrue(plan(0x4004,8)['release_old'])
        self.assertFalse(plan(4,8,old_present=False)['release_old'])
        self.assertEqual(plan(0xc008,4)['control_word'],0xc008)
        self.assertEqual(plan(0xc008,4,force=True)['control_word'],4)

    def test_complete_rebuild_receipt(self):
        from reference.supplemental_pose_records import plan_supplemental_rebuild
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/supplemental_rebuild_validation.json').read_text())
        self.assertEqual(receipt['cases'],48)
        for sample in receipt['samples']:
            self.assertEqual(plan_supplemental_rebuild(**sample['inputs']),sample['result'])

    def test_rebuild_does_not_relocate_discarded_records(self):
        from reference.supplemental_pose_records import plan_supplemental_rebuild
        result=plan_supplemental_rebuild((3<<16)|4,8)
        self.assertTrue(result['reserve']['replace'])
        self.assertEqual(result['reserve']['relocation_bytes'],0)
        self.assertEqual(result['final_control_word'],(8<<16)|8)
