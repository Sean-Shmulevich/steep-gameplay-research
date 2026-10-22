import json
from pathlib import Path
import struct
import unittest
from reference.animation_channels import combine_float_channel as combine


class FloatChannelMathTests(unittest.TestCase):
    def test_native_helper_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/float_channel_math_validation.json').read_text())
        self.assertEqual(receipt['cases'], 160)
        for sample in receipt['samples']:
            result = combine(**sample['inputs'])
            fmt = '<%df' % len(result)
            self.assertEqual(struct.pack(fmt, *result), struct.pack(fmt, *sample['result']))

    def test_mode_and_type_distinction(self):
        self.assertEqual(combine([10], [20], .5, 1, 4), (15,))
        self.assertEqual(combine([10]*4, [20]*4, .5, 5, 4), (20,)*4)
        self.assertEqual(combine([10]*4, [20]*4, .5, 5, 0), (15,)*4)
        self.assertEqual(combine([10], [20], 1.5, 1, 0), (25,))

    def test_unsupported_types_are_not_guessed(self):
        for kind in (0,2,3,4,6,15):
            with self.assertRaises(ValueError): combine([1], [2], .5, kind, 0)

    def test_original_arithmetic_routing_receipt(self):
        from reference.animation_channels import plan_arithmetic_channel_route
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/arithmetic_channel_route_validation.json').read_text())
        self.assertEqual(receipt['cases'], 112)
        for sample in receipt['samples']:
            plan = plan_arithmetic_channel_route(**sample['inputs'])
            self.assertEqual([dict(helper=plan['helper'], sources=plan['sources'], index=i)
                              for i in plan['indices']], sample['events'])

    def test_unweighted_original_helper(self):
        from reference.animation_channels import combine_unweighted_channel
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/unweighted_channel_validation.json').read_text())
        self.assertEqual(receipt['cases'], 320)
        for sample in receipt['samples']:
            result = combine_unweighted_channel(**sample['inputs'])
            fmt = '<B' if sample['inputs']['kind'] == 0 else '<%df' % len(result)
            self.assertEqual(struct.pack(fmt, *result), struct.pack(fmt, *sample['result']))

    def test_unweighted_wrap_order_and_unchanged_destination(self):
        from reference.animation_channels import combine_unweighted_channel as combine
        self.assertEqual(combine([250], [10], [99], 0), (4,))
        self.assertEqual(combine([], [], [99], 2), (99,))
        self.assertEqual(combine([1,0,0,0], [0,1,0,0], [], 6), (0,0,1,0))
        self.assertEqual(combine([0,1,0,0], [1,0,0,0], [], 6), (0,0,-1,0))
        self.assertEqual(combine([0,0,0,2], [0,0,0,3], [], 6), (0,0,0,6))

    def test_complete_float_bank_receipt(self):
        from reference.animation_channels import combine_float_channel_batch
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/joined_float_bank_validation.json').read_text())
        self.assertEqual(receipt['cases'], 80)
        for sample in receipt['samples']:
            result = combine_float_channel_batch(**sample['inputs'])
            for actual, expected in zip(result['channels'], sample['channels']):
                fmt = '<%df' % len(actual)
                self.assertEqual(struct.pack(fmt, *actual), struct.pack(fmt, *expected))

    def test_joined_near_one_scalar_changes_helper_family(self):
        from reference.animation_channels import combine_float_channel_batch as batch
        args = dict(first=[[10]], second=[[20]], previous=[[-1]], kinds=[1], mode=4)
        self.assertEqual(batch(**args, weight=1)['channels'], [(30,)])
        self.assertEqual(batch(**args, weight=1, exclusion_mask=2)['channels'], [(-1,)])
        self.assertLess(batch(**args, weight=.999)['channels'][0][0], 11)

    def test_weighted_rotation_helpers(self):
        from reference.animation_channels import combine_rotation_channel
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/weighted_rotation_channel_validation.json').read_text())
        self.assertEqual(receipt['cases'],160)
        for sample in receipt['samples']:
            used=[]
            def seed(n):
                index=len(used);used.append(n)
                self.assertEqual(n,sample['lengths'][index]);return sample['seeds'][index]
            result=combine_rotation_channel(**sample['inputs'],reciprocal_sqrt=seed)
            self.assertEqual(len(used),len(sample['seeds']))
            self.assertEqual(struct.pack('<4f',*result),struct.pack('<4f',*sample['result']))

    def test_joined_numeric_bank_receipt(self):
        from reference.animation_channels import combine_numeric_channel_batch
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/joined_numeric_bank_validation.json').read_text())
        self.assertEqual(receipt['cases'],100)
        for sample in receipt['samples']:
            used=[]
            def seed(n):
                index=len(used);used.append(n)
                self.assertEqual(n,sample['lengths'][index]);return sample['seeds'][index]
            result=combine_numeric_channel_batch(**sample['inputs'],reciprocal_sqrt=seed)
            self.assertEqual(len(used),len(sample['seeds']))
            for actual,expected in zip(result['channels'],sample['channels']):
                fmt='<%df'%len(actual)
                self.assertEqual(struct.pack(fmt,*actual),struct.pack(fmt,*expected))

    def test_weighted_quaternion_requires_seed_but_skipped_one_does_not(self):
        from reference.animation_channels import combine_numeric_channel_batch as batch
        args=dict(first=[[0,0,0,1]],second=[[1,0,0,0]],previous=[[9]*4],
                  kinds=[6],mode=4,weight=.5)
        with self.assertRaises(ValueError): batch(**args)
        self.assertEqual(batch(**args,exclusion_mask=64)['channels'],[(9,9,9,9)])

    def test_nonempty_pose_bank_receipt(self):
        from reference.animation_channels import evaluate_numeric_pose_bank
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/joined_pose_bank_validation.json').read_text())
        self.assertEqual(receipt['cases'],100)
        for sample in receipt['samples']:
            used=[]
            def seed(n):
                index=len(used);used.append(n)
                self.assertEqual(n,sample['lengths'][index]);return sample['seeds'][index]
            result=evaluate_numeric_pose_bank(**sample['inputs'],reciprocal_sqrt=seed)
            self.assertEqual(len(used),len(sample['seeds']))
            for actual,expected in zip(result['channels'],sample['channels']):
                fmt='<%df'%len(actual)
                self.assertEqual(struct.pack(fmt,*actual),struct.pack(fmt,*expected))
            for actual,expected in zip(result['records'],sample['records']):
                self.assertEqual(actual['id'],expected['id'])
                for field in ('vector','rotation'):
                    self.assertEqual(struct.pack('<4f',*actual[field]),struct.pack('<4f',*expected[field]))

    def test_numeric_bank_status_in_complete_entry(self):
        from reference.animation_channels import evaluate_numeric_pose_bank
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/numeric_bank_status_validation.json').read_text())
        self.assertEqual(receipt['cases'],48)
        for sample in receipt['samples']:
            used=[]
            def seed(n):
                index=len(used);used.append(n)
                self.assertEqual(n,sample['lengths'][index]);return sample['seeds'][index]
            result=evaluate_numeric_pose_bank(**sample['inputs'],reciprocal_sqrt=seed)
            self.assertEqual(result['flags'],sample['destination_flags'])
            self.assertEqual(len(used),len(sample['seeds']))
            self.assertEqual(result['records'],sample['records'])

    def test_empty_copy_does_not_set_status_in_arithmetic_route(self):
        from reference.animation_channels import numeric_bank_status_after,plan_arithmetic_channel_route
        for kinds,mask,expected in [([],0,0),([1],2,0),([1],0,1<<27)]:
            route=plan_arithmetic_channel_route(0,1,False,kinds,mask)
            self.assertEqual(numeric_bank_status_after(0,route),expected)

    def test_grouped_pose_bank_receipt(self):
        from reference.animation_channels import evaluate_numeric_pose_bank
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/grouped_pose_bank_validation.json').read_text())
        self.assertEqual(receipt['cases'],48)
        for sample in receipt['samples']:
            used=[]
            def seed(n):
                index=len(used);used.append(n)
                self.assertEqual(n,sample['lengths'][index]);return sample['seeds'][index]
            result=evaluate_numeric_pose_bank(**sample['inputs'],reciprocal_sqrt=seed)
            self.assertEqual(len(used),len(sample['seeds']))
            self.assertEqual(result['flags'],sample['destination_flags'])
            self.assertEqual([list(c) for c in result['channels']],sample['channels'])
            self.assertEqual(result['records'],sample['records'])
            selected=result['range']
            self.assertTrue(all(selected['first']<=i<selected['first']+selected['count']
                                for i in result['route']['indices']))

    def test_aliased_storage_native_receipt(self):
        from reference.animation_channels import evaluate_float_bank_storage
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/aliased_float_bank_validation.json').read_text())
        self.assertEqual(receipt['cases'],16)
        for sample in receipt['samples']:
            result=evaluate_float_bank_storage(bytes.fromhex(sample['storage']),**sample['inputs'])
            self.assertEqual(result['storage'].hex(),sample['result'])
            self.assertEqual(result['flags'],sample['flags'])

    def test_later_channel_reads_prior_write(self):
        from reference.animation_channels import evaluate_float_bank_storage
        values=[1.]*4+[10.]*4+[20.]*4+[30.]*4
        storage=struct.pack('<16f',*values)
        result=evaluate_float_bank_storage(storage,0,32,16,[(0,5),(16,5)],0,.5)
        out=struct.unpack('<16f',result['storage'])
        self.assertEqual(out[4:8],(10.5,)*4)
        self.assertEqual(out[8:12],(20.25,)*4)

    def test_outer_group_wrapper_receipt(self):
        from reference.animation_channels import plan_bank_group_calls
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/bank_group_wrapper_validation.json').read_text())
        self.assertEqual(receipt['cases'],80)
        for sample in receipt['samples']:
            self.assertEqual(plan_bank_group_calls(**sample['inputs']),sample['calls'])

    def test_wrapper_multibit_and_all_sentinel_are_distinct(self):
        from reference.animation_channels import plan_bank_group_calls as plan
        self.assertEqual([c['group_mask'] for c in plan(0,3,3,.5,0)],[1,2])
        self.assertEqual(plan(0,0,3,.5,0),[])
        self.assertEqual([c['group_mask'] for c in plan(0,65535,0,.5,0)],[65535])

    def test_pose_operation_route_receipt(self):
        from reference.animation_channels import plan_pose_operation_route
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/pose_operation_route_validation.json').read_text())
        self.assertEqual(receipt['cases'],80)
        for sample in receipt['samples']:
            self.assertEqual(plan_pose_operation_route(**sample['inputs']),sample['result'])

    def test_operation_weight_mutation_is_not_clamped(self):
        from reference.animation_channels import plan_pose_operation_route as plan
        result=plan(0,False,5,3,1,0,0x38,1.25)
        self.assertEqual(result['weight'],-.25)
        self.assertTrue(result['weight_written'])
        self.assertFalse(result['swap'])
        self.assertEqual(result['range_selector'],7)

    def test_pose_command_flag_decode_receipt(self):
        from reference.animation_channels import pose_command_source_kinds,plan_pose_operation_route
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/pose_command_flags_validation.json').read_text())
        self.assertEqual(receipt['cases'],256)
        for sample in receipt['samples']:
            kinds=pose_command_source_kinds(sample['flags'])
            self.assertEqual(kinds,sample['result'])
            result=plan_pose_operation_route(0,False,65535,3,
                component_flags=0,weight=.25,**kinds)
            self.assertEqual(result['route'],'mode_0' if kinds['first_kind']==kinds['second_kind'] else 'mode_4')

    def test_manager_bank_group_release_receipt(self):
        from reference.animation_channels import release_pose_bank_groups
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/bank_group_release_validation.json').read_text())
        self.assertEqual(receipt['cases'],72)
        for sample in receipt['samples']:
            self.assertEqual(release_pose_bank_groups(**sample['inputs']),sample['result'])

    def test_group_release_counter_decrements_once_not_per_bit(self):
        from reference.animation_channels import release_pose_bank_groups as release
        result=release([65535,65535],['x','x'],'x',3,0,3,2)
        self.assertEqual(result['supplemental_counter'],1)
        self.assertFalse(result['reset_storage'])
        self.assertEqual(result['entry_masks'],[65532,65535])
        self.assertEqual(result['bank_flags'],1<<26)
