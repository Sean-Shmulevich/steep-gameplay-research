"""Synthetic native-receipt comparisons; rotation remains an external service."""
import copy
import json
from pathlib import Path
import struct
import unittest
from reference.animation_channels import blend_auxiliary_pose_triplet as blend

RECEIPT = Path(__file__).resolve().parents[1] / 'native/snow_host/auxiliary_triplet_validation.json'


def packed(bank):
    return b''.join(struct.pack('<8f', *p['vector'], *p['rotation'])
                    for p in bank['poses']) + struct.pack('<3fI', *bank['weights'], bank['flags'])


class AuxiliaryPoseTripletTests(unittest.TestCase):
    def test_original_instruction_receipt_and_call_order(self):
        receipt = json.loads(RECEIPT.read_text())
        self.assertEqual(receipt['cases'], 32)
        for sample in receipt['samples']:
            with self.subTest(inputs=sample['inputs']):
                calls = []
                inputs = copy.deepcopy(sample['inputs'])
                def rotate(a, b, weight):
                    calls.append([a, b, weight])
                    return [11, 12, 13, 14]
                actual = blend(**inputs, rotate=rotate)
                self.assertEqual(packed(actual), packed(sample['result']))
                self.assertEqual(calls, sample['rotation_calls'])
                self.assertEqual(inputs, sample['inputs'])

    def test_null_inputs_retain_destination_without_rotation(self):
        inputs = json.loads(RECEIPT.read_text())['samples'][-1]['inputs']
        for key in ('first', 'second', 'previous'):
            case = copy.deepcopy(inputs)
            case[key] = None
            self.assertEqual(blend(**case, rotate=lambda *args: self.fail('unexpected rotation')),
                             case['previous'])

    def test_authored_shape_and_finite_contract(self):
        inputs = json.loads(RECEIPT.read_text())['samples'][-1]['inputs']
        for bank_name in ('first', 'second', 'previous'):
            for field, value in [('poses', []), ('weights', [1]), ('flags', -1)]:
                case = copy.deepcopy(inputs)
                case[bank_name][field] = value
                with self.assertRaises(ValueError): blend(**case, rotate=None)
            for field in ('vector', 'rotation'):
                case = copy.deepcopy(inputs)
                case[bank_name]['poses'][0][field] = [0, 0, 1]
                with self.assertRaises(ValueError): blend(**case, rotate=None)
        for value in (float('nan'), float('inf')):
            case = copy.deepcopy(inputs)
            case['weight'] = value
            with self.assertRaises(ValueError): blend(**case, rotate=None)


class AuxiliarySphericalTests(unittest.TestCase):
    def test_complete_original_fallback_receipt(self):
        from reference.supplemental_pose_records import spherical_auxiliary_rotation
        receipt=json.loads((RECEIPT.parent/'auxiliary_spherical_validation.json').read_text())
        self.assertEqual(receipt['cases'],70)
        for sample in receipt['samples']:
            events=iter(sample['services'])
            def service(name):
                def call(value):
                    event=next(events)
                    self.assertEqual((name,value),(event['service'],event['input']))
                    return event['output']
                return call
            seeds=[]
            def seed(length):
                self.assertEqual(length,sample['normalization']['length'])
                seeds.append(length)
                return sample['normalization']['seed']
            result=spherical_auxiliary_rotation(**sample['inputs'],arccos=service('arccos'),
                                               sine=service('sine'),reciprocal_sqrt=seed)
            self.assertEqual(struct.pack('<4f',*result),struct.pack('<4f',*sample['result']))
            self.assertIsNone(next(events,None))
            self.assertEqual(len(seeds),int(bool(sample['normalization'])))

    def test_outside_dot_domain_retains_second_without_services(self):
        from reference.supplemental_pose_records import spherical_auxiliary_rotation
        def fail(*args):self.fail('unexpected math service')
        for second in ([0,0,0,1],[0,0,0,-1],[0,0,0,2]):
            self.assertEqual(spherical_auxiliary_rotation([0,0,0,1],second,.25,1e-5,
                                                         fail,fail,fail),second)


class JoinedAuxiliaryTripletTests(unittest.TestCase):
    def test_complete_original_triplet_with_actual_rotation_services(self):
        from reference.animation_channels import evaluate_auxiliary_pose_triplet
        receipt=json.loads((RECEIPT.parent/'auxiliary_triplet_joined_validation.json').read_text())
        self.assertEqual(receipt['cases'],160)
        for sample in receipt['samples']:
            events=iter(sample['services']);seeds=iter(sample['normalizations'])
            def service(name):
                def call(value):
                    event=next(events)
                    self.assertEqual((name,value),(event['service'],event['input']))
                    return event['output']
                return call
            def seed(length):
                event=next(seeds)
                self.assertEqual(length,event['length'])
                return event['seed']
            result=evaluate_auxiliary_pose_triplet(**sample['inputs'],arccos=service('arccos'),
                                                  sine=service('sine'),reciprocal_sqrt=seed)
            self.assertEqual(packed(result),packed(sample['result']))
            self.assertIsNone(next(events,None));self.assertIsNone(next(seeds,None))


class PoseOperationTailTests(unittest.TestCase):
    def test_original_tail_dispatch_receipt(self):
        from reference.animation_channels import plan_pose_operation_tail
        receipt=json.loads((RECEIPT.parent/'pose_operation_tail_validation.json').read_text())
        self.assertEqual(receipt['cases'],192)
        for sample in receipt['samples']:
            self.assertEqual(plan_pose_operation_tail(**sample['inputs']),sample['result'])

    def test_zero_mask_still_marks_and_releases_both_uncached_sources(self):
        from reference.animation_channels import plan_pose_operation_tail
        result=plan_pose_operation_tail(0,8,False,65535,0,False,False)
        self.assertEqual(result,dict(keyed_blend=False,completed_mask=8,
            events=['mark_completed_mask','release_first','release_second']))


class SharedSourceReleaseTests(unittest.TestCase):
    def test_original_tail_and_manager_composition(self):
        from reference.animation_channels import apply_pose_source_releases
        receipt=json.loads((RECEIPT.parent/'shared_source_release_validation.json').read_text())
        self.assertEqual(receipt['cases'],72)
        for sample in receipt['samples']:
            original=copy.deepcopy(sample['inputs'])
            self.assertEqual(apply_pose_source_releases(**sample['inputs']),sample['result'])
            self.assertEqual(sample['inputs'],original)

    def test_shared_source_decrements_only_once_but_retains_two_effects(self):
        from reference.animation_channels import apply_pose_source_releases
        bank=dict(flags=0,supplemental_mask=3,supplemental_counter=2)
        result=apply_pose_source_releases([65535],['a'],{'a':bank},'a','a',False,False,1)
        self.assertEqual(result['banks']['a']['supplemental_counter'],1)
        self.assertEqual(result['banks']['a']['supplemental_mask'],2)
        self.assertEqual(len(result['effects']),2)
        self.assertFalse(any(effect['reset_storage'] for effect in result['effects']))


class JoinedPoseTailTests(unittest.TestCase):
    def test_original_tail_with_blend_and_release_effects(self):
        from reference.animation_channels import evaluate_pose_operation_tail
        receipt=json.loads((RECEIPT.parent/'pose_tail_joined_validation.json').read_text())
        self.assertEqual(receipt['cases'],48)
        for sample in receipt['samples']:
            events=iter(sample['services']);seeds=iter(sample['normalizations'])
            def service(name):
                def call(value):
                    event=next(events)
                    self.assertEqual((name,value),(event['service'],event['input']))
                    return event['output']
                return call
            def seed(length):
                event=next(seeds);self.assertEqual(length,event['length'])
                return event['seed']
            inputs=copy.deepcopy(sample['inputs'])
            result=evaluate_pose_operation_tail(**inputs,arccos=service('arccos'),
                                               sine=service('sine'),reciprocal_sqrt=seed)
            self.assertEqual(result,sample['result'])
            for key,bank in result['banks'].items():
                self.assertEqual(packed(bank),packed(sample['result']['banks'][key]))
            self.assertEqual(inputs,sample['inputs'])
            self.assertIsNone(next(events,None));self.assertIsNone(next(seeds,None))

    def test_destination_alias_is_explicitly_unvalidated(self):
        from reference.animation_channels import evaluate_pose_operation_tail
        case=json.loads((RECEIPT.parent/'pose_tail_joined_validation.json').read_text())['samples'][0]['inputs']
        case['destination']=case['first']
        with self.assertRaisesRegex(ValueError,'aliasing'):
            evaluate_pose_operation_tail(**case,arccos=None,sine=None,reciprocal_sqrt=None)


class OrdinaryPoseOperationTests(unittest.TestCase):
    def test_complete_original_ordinary_operation(self):
        from reference.animation_channels import evaluate_ordinary_pose_operation
        receipt=json.loads((RECEIPT.parent/'ordinary_pose_operation_validation.json').read_text())
        self.assertEqual(receipt['cases'],96)
        for sample in receipt['samples']:
            events=iter(sample['services']);seeds=iter(sample['normalizations'])
            def service(name):
                def call(value):
                    event=next(events);self.assertEqual((name,value),(event['service'],event['input']))
                    return event['output']
                return call
            def seed(length):
                event=next(seeds);self.assertEqual(length,event['length']);return event['seed']
            result=evaluate_ordinary_pose_operation(**sample['inputs'],arccos=service('arccos'),
                                                    sine=service('sine'),reciprocal_sqrt=seed)
            self.assertEqual(json.loads(json.dumps(result)),sample['result'])
            for name,bank in result['banks'].items():
                for actual,expected in zip(bank['channels'],sample['result']['banks'][name]['channels']):
                    fmt='<%df'%len(actual)
                    self.assertEqual(struct.pack(fmt,*actual),struct.pack(fmt,*expected))
            self.assertIsNone(next(events,None));self.assertIsNone(next(seeds,None))

    def test_complete_original_mixed_operation(self):
        from reference.animation_channels import evaluate_ordinary_pose_operation
        receipt=json.loads((RECEIPT.parent/'ordinary_pose_mixed_validation.json').read_text())
        self.assertEqual(receipt['cases'],96)
        for sample in receipt['samples']:
            events=iter(sample['services']);seeds=iter(sample['normalizations'])
            def service(name):
                def call(value):
                    event=next(events);self.assertEqual((name,value),(event['service'],event['input']))
                    return event['output']
                return call
            def seed(length):
                event=next(seeds);self.assertEqual(length,event['length']);return event['seed']
            result=evaluate_ordinary_pose_operation(**sample['inputs'],arccos=service('arccos'),
                                                    sine=service('sine'),reciprocal_sqrt=seed)
            self.assertEqual(json.loads(json.dumps(result)),sample['result'])
            for name,bank in result['banks'].items():
                for actual,expected in zip(bank['channels'],sample['result']['banks'][name]['channels']):
                    fmt='<%df'%len(actual)
                    self.assertEqual(struct.pack(fmt,*actual),struct.pack(fmt,*expected))
            self.assertIsNone(next(events,None));self.assertIsNone(next(seeds,None))

    def test_special_service_not_silently_substituted(self):
        from reference.animation_channels import evaluate_ordinary_pose_operation
        case=json.loads((RECEIPT.parent/'ordinary_pose_operation_validation.json').read_text())['samples'][0]['inputs']
        case['operation'].update(operation_kind=5,special_ready=True)
        with self.assertRaises(NotImplementedError):
            evaluate_ordinary_pose_operation(**case,arccos=None,sine=None,reciprocal_sqrt=None)


class PoseResourceLookupTests(unittest.TestCase):
    def test_original_lookup_receipt(self):
        from reference.animation_channels import lookup_pose_resource
        receipt=json.loads((RECEIPT.parent/'pose_resource_lookup_validation.json').read_text())
        self.assertEqual(receipt['cases'],78)
        for sample in receipt['samples']:
            self.assertEqual(lookup_pose_resource(**sample['inputs']),sample['result'])

    def test_first_duplicate_and_unsigned_order(self):
        from reference.animation_channels import lookup_pose_resource
        self.assertEqual(lookup_pose_resource([(1,8),(1,9),(0xffffffff,4)],1),8)
        with self.assertRaises(ValueError):lookup_pose_resource([(0xffffffff,4),(1,8)],1)

    def test_lookup_joined_receipt_preserves_full_operation_results(self):
        previous=json.loads((RECEIPT.parent/'ordinary_pose_mixed_validation.json').read_text())
        joined=json.loads((RECEIPT.parent/'ordinary_pose_lookup_joined_validation.json').read_text())
        self.assertEqual(joined['cases'],96)
        self.assertEqual(previous['samples'],joined['samples'])


class UninterceptedOrdinaryOperationTests(unittest.TestCase):
    def test_actual_provider_lookup_preserves_operation_results(self):
        supplied=json.loads((RECEIPT.parent/'ordinary_pose_lookup_joined_validation.json').read_text())
        complete=json.loads((RECEIPT.parent/'ordinary_pose_unintercepted_validation.json').read_text())
        self.assertEqual(complete['cases'],96)
        self.assertEqual(supplied['samples'],complete['samples'])
        self.assertFalse(complete['game_process'])


class HermitePosePairTests(unittest.TestCase):
    def test_original_special_pair_receipt(self):
        from reference.animation_channels import hermite_pose_pair
        receipt=json.loads((RECEIPT.parent/'hermite_pose_pair_validation.json').read_text())
        self.assertEqual(receipt['cases'],40)
        for sample in receipt['samples']:
            seen=[]
            def seed(length):
                seen.append(length);self.assertEqual(length,sample['normalization']['length'])
                return sample['normalization']['seed']
            result=hermite_pose_pair(**sample['inputs'],reciprocal_sqrt=seed)
            self.assertEqual(result,sample['result'])
            self.assertEqual(len(seen),int(bool(sample['normalization'])))
            self.assertEqual(struct.pack('<8f',*result['vector'],*result['rotation']),
                             struct.pack('<8f',*sample['result']['vector'],*sample['result']['rotation']))


class SpecialPoseWalkTests(unittest.TestCase):
    def test_original_store_order_and_tangent_indices(self):
        from reference.animation_channels import plan_special_pose_walk
        receipt=json.loads((RECEIPT.parent/'special_pose_walk_validation.json').read_text())
        self.assertEqual(receipt['cases'],48)
        for sample in receipt['samples']:
            self.assertEqual(plan_special_pose_walk(**sample['inputs']),sample['result'])

    def test_boundary_quaternion_lookahead_is_preserved(self):
        from reference.animation_channels import plan_special_pose_walk
        result=plan_special_pose_walk([[0x2c52cbb0,5],[0,6]],1,65535,[])
        self.assertEqual(result['writes'],[dict(channel=0,kind='vector',tangent=0),
                                         dict(channel=1,kind='rotation',tangent=0)])
        with self.assertRaisesRegex(ValueError,'lookahead'):
            plan_special_pose_walk([[0x2c52cbb0,5]],1,65535,[])


class SpecialPoseBankTests(unittest.TestCase):
    def test_complete_special_helper_with_nonzero_tangents(self):
        from reference.animation_channels import evaluate_special_pose_bank
        receipt=json.loads((RECEIPT.parent/'special_pose_bank_validation.json').read_text())
        self.assertEqual(receipt['cases'],48)
        for sample in receipt['samples']:
            seeds=iter(sample['normalizations'])
            def seed(length):
                event=next(seeds);self.assertEqual(length,event['length']);return event['seed']
            original=copy.deepcopy(sample['inputs'])
            result=evaluate_special_pose_bank(**sample['inputs'],reciprocal_sqrt=seed)
            self.assertEqual(result,sample['result'])
            for actual,expected in zip(result['channels'],sample['result']['channels']):
                self.assertEqual(struct.pack('<4f',*actual),struct.pack('<4f',*expected))
            self.assertEqual(original,sample['inputs']);self.assertIsNone(next(seeds,None))


class TangentStorageCloneTests(unittest.TestCase):
    def test_original_clone_dispatch_slices(self):
        from reference.animation_channels import plan_tangent_storage_clone
        receipt=json.loads((RECEIPT.parent/'tangent_clone_validation.json').read_text())
        self.assertEqual(receipt['cases'],32)
        for sample in receipt['samples']:
            self.assertEqual(plan_tangent_storage_clone(**sample['inputs']),sample['result'])


class PoseCopyGuardTests(unittest.TestCase):
    def test_original_predicate_kind_flag_and_float_boundaries(self):
        from reference.animation_channels import pose_operation_copy_guard
        receipt=json.loads((RECEIPT.parent/'pose_copy_guard_validation.json').read_text())
        self.assertEqual(receipt['cases'],384)
        for sample in receipt['samples']:
            self.assertEqual(pose_operation_copy_guard(**sample['inputs']),sample['result'])

    def test_special_early_return_precedes_other_flags_and_scalar_limit(self):
        from reference.animation_channels import pose_operation_copy_guard
        self.assertFalse(pose_operation_copy_guard(5,2,100.,1.))
        self.assertTrue(pose_operation_copy_guard(5,6,100.,1.))
