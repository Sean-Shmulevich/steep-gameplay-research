"""Synthetic regression evidence; original instruction checks remain private."""
import json
import struct
import unittest
from pathlib import Path
from reference.central_impulse import f32, helper_response_filter
from reference.ground_response_pose import consume_displacement, pose_length_correction


class GroundResponsePoseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/ground_response_pose_validation.json').read_text())

    def test_original_reader_and_swap_results(self):
        self.assertEqual(len(self.evidence['reader']), 24)
        self.assertEqual(len(self.evidence['swap_then_reader']), 6)
        for row in self.evidence['reader'] + self.evidence['swap_then_reader']:
            with self.subTest(row=row):
                actual = consume_displacement(row['previous'], row['published'], row['decay_mode'])
                self.assertEqual(struct.pack('<f', actual), struct.pack('<f', row['result']))

    def test_original_pose_scalar_results(self):
        self.assertEqual(len(self.evidence['pose']), 108)
        for row in self.evidence['pose']:
            args = {k:v for k,v in row.items() if k != 'result'}
            with self.subTest(args=args):
                actual = pose_length_correction(**args)
                self.assertTrue(actual['active'])
                for key in ('stored_length', 'correction_scale'):
                    self.assertEqual(struct.pack('<f', actual[key]), struct.pack('<f', row['result'][key]))

    def test_unused_branch_inputs_are_not_read(self):
        invalid = object()
        self.assertEqual(consume_displacement(invalid, .8, False), f32(.8))
        self.assertEqual(consume_displacement(.5, invalid, True), f32(.5*f32(.9)))
        result = pose_length_correction(1, invalid, invalid, True, True, invalid, invalid)
        self.assertEqual(result['stored_length'], 1)
        self.assertEqual(result['correction_scale'], 0)

    def test_short_length_preserves_stored_value(self):
        edge = f32(.01)
        for length in (0, edge, -edge):
            result = pose_length_correction(length, object(), object(), False, False, object(), object())
            self.assertFalse(result['active'])
            self.assertIsNone(result['stored_length'])
            self.assertEqual(result['correction_scale'], 0)
        bits = struct.unpack('<I', struct.pack('<f', edge))[0]
        above = struct.unpack('<f', struct.pack('<I', bits+1))[0]
        self.assertTrue(pose_length_correction(above, 0, 0, False, True, 0, 2)['active'])

    def test_filter_publication_can_feed_pose(self):
        # Authored composition timing; no claim of native same-frame execution.
        filtered = helper_response_filter(0, 0, (0,0,30), (0,0,1), 1/60)
        displacement = consume_displacement(0, filtered['displacement'], False)
        pose = pose_length_correction(1, displacement, 1, False, False, .2, 1.5)
        self.assertGreater(displacement, 0)
        self.assertLess(pose['stored_length'], 1)
        decayed = consume_displacement(displacement, object(), True)
        later = pose_length_correction(1, decayed, 1, False, False, .2, 1.5)
        self.assertGreater(later['stored_length'], pose['stored_length'])

    def test_mode_contract_rejects_ambiguous_values(self):
        with self.assertRaises(ValueError): consume_displacement(0,0,1)
        with self.assertRaises(ValueError): pose_length_correction(1,0,1,0,False,0,2)


class ReferencePoseVectorTests(unittest.TestCase):
    def test_original_vector_and_store_results(self):
        from reference.ground_response_pose import reference_pose_correction
        evidence = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/ground_response_pose_vector_validation.json').read_text())
        self.assertEqual(evidence['cases'], 160)
        for i, row in enumerate(evidence['rows']):
            calls = []
            def seed(n):
                calls.append(n)
                return row['rsqrt_estimate']
            with self.subTest(case=i):
                result = reference_pose_correction(**row['inputs'], reciprocal_sqrt=seed)
                self.assertEqual(len(calls), int(result['active']))
                for key in ('correction', 'transformed'):
                    self.assertEqual(struct.pack('<4f', *result[key]),
                                     struct.pack('<4f', *row['result'][key]))
                self.assertEqual(result['stored_length'], row['result']['stored_length'])
                self.assertEqual(result['input_length'], row['result']['input_length'])

    def test_identity_rotation_correction_direction(self):
        import math
        from reference.ground_response_pose import reference_pose_correction
        r = reference_pose_correction((0,0,1,0), (0,0,0,1), .8, 1,
                                      False, False, .2, 1.5, lambda n:1/math.sqrt(n))
        self.assertAlmostEqual(r['correction'][2], -.4, places=6)
        self.assertEqual(r['correction'][0:2], (0.,0.))
        self.assertAlmostEqual(r['stored_length'], .6, places=6)

    def test_invalid_provider_data_policy(self):
        from reference.ground_response_pose import reference_pose_correction
        for vector, rotation in (((1,2,3), (0,0,0,1)),
                                 ((1,2,3,0), (0,0,0,0)),
                                 ((float('nan'),0,1,0), (0,0,0,1))):
            with self.assertRaises(ValueError):
                reference_pose_correction(vector, rotation, 0, 1, False, False, 0, 2, lambda n:1)


class StoredLengthFilterTests(unittest.TestCase):
    def test_original_signed_reach_cases(self):
        from reference.ground_response_pose import stored_length_filter
        evidence = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/stored_length_filter_validation.json').read_text())
        self.assertEqual(evidence['cases'], 144)
        for i, row in enumerate(evidence['rows']):
            with self.subTest(case=i):
                result = stored_length_filter(**row['inputs'])
                for key in ('correction', 'corrected_reference'):
                    self.assertEqual(struct.pack('<4f', *result[key]),
                                     struct.pack('<4f', *row['result'][key]))

    def test_perpendicular_distance_is_zero_not_unsigned_length(self):
        from reference.ground_response_pose import stored_length_filter
        r = stored_length_filter((0,0,1,0), (1,0,1,0), (0,0,0,0),
                                 (0,0,1,0), (0,0,0,0), 1, 1)
        self.assertEqual(r['signed_distances'], (0.,1.))
        self.assertEqual(r['correction'], (0.,0.,.5,0.))

    def test_zero_blend_retains_previous_correction(self):
        from reference.ground_response_pose import stored_length_filter
        old = (.2,-.3,.4,0.)
        r = stored_length_filter((0,0,1,0), (0,0,0,0), (0,0,0,0),
                                 (0,0,1,0), old, 2, 0)
        self.assertEqual(r['correction'], tuple(f32(x) for x in old))

    def test_pose_length_producer_composes_with_filter(self):
        from reference.ground_response_pose import stored_length_filter
        length = pose_length_correction(1, .8, 1, False, False, .2, 1.5)['stored_length']
        r = stored_length_filter((0,0,1,0), (0,0,0,0), (0,0,0,0),
                                 (0,0,1,0), (0,0,0,0), length, 1)
        self.assertAlmostEqual(r['corrected_reference'][2], .6, places=6)


class ReachLimitTests(unittest.TestCase):
    def args(self):
        return dict(endpoints=((0,0,0,0),)*2, signed_distances=(2.,2.),
                    axis=(0,0,1,0), above_directions=((1,0,0,0),)*2,
                    below_directions=((0,1,0,0),)*2, velocity=(0,0,0,0),
                    rest_lengths=(1.,1.), lower=.2, upper=1.5)

    def test_original_reach_cases(self):
        from reference.ground_response_pose import reach_limit_endpoints
        evidence = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/reach_limits_validation.json').read_text())
        self.assertEqual(evidence['cases'], 192)
        for i, row in enumerate(evidence['rows']):
            with self.subTest(case=i):
                result = reach_limit_endpoints(**row['inputs'])
                for actual, expected in zip(result['endpoints'], row['result']['endpoints']):
                    self.assertEqual(struct.pack('<4f', *actual), struct.pack('<4f', *expected))

    def test_strict_speed_boundary_only_suppresses_direction_term(self):
        from reference.ground_response_pose import reach_limit_endpoints
        args = self.args(); args['velocity'] = (.5,.5,0,0)
        at = reach_limit_endpoints(**args)
        self.assertFalse(at['moving'])
        self.assertEqual(at['endpoints'][0], (0.,0.,.5,0.))
        args['velocity'] = (.5,.5,.001,0)
        above = reach_limit_endpoints(**args)
        self.assertTrue(above['moving'])
        self.assertEqual(above['endpoints'][0], (f32(.15),0.,.5,0.))

    def test_rest_length_widens_low_speed_interval(self):
        from reference.ground_response_pose import reach_limit_endpoints
        args = self.args(); args['rest_lengths'] = (.1,3.)
        r = reach_limit_endpoints(**args)
        self.assertEqual(r['bounds'], ((f32(.1),1.5),(f32(.2),3.)))
        self.assertEqual(r['endpoints'][1], (0.,0.,0.,0.))

    def test_lower_branch_cap_and_gain(self):
        from reference.ground_response_pose import reach_limit_endpoints
        args = self.args(); args.update(signed_distances=(0.,0.), lower=1., upper=2.)
        r = reach_limit_endpoints(**args)
        self.assertEqual(r['endpoints'][0][1], .25)
        self.assertAlmostEqual(r['endpoints'][0][2], -.925, places=6)


class EndpointOutputTests(unittest.TestCase):
    def args(self):
        return dict(origins=((0,0,0,0),)*2, rotations=((0,0,0,1),)*2,
                    deltas=((1,0,0,0),)*2, previous=((0,0,1,0),)*2,
                    blend=1, offsets=(0,0), contact_scalars=(0,1),
                    decay_mode=False, reference_z=0)

    def test_original_output_stores(self):
        from reference.ground_response_pose import endpoint_output_stage
        evidence = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/endpoint_output_validation.json').read_text())
        self.assertEqual(evidence['cases'], 216)
        for i, row in enumerate(evidence['rows']):
            with self.subTest(case=i):
                result = endpoint_output_stage(**row['inputs'])
                for key in ('smoothed', 'positions'):
                    for actual, expected in zip(result[key], row['result'][key]):
                        self.assertEqual(struct.pack('<4f', *actual), struct.pack('<4f', *expected))
                self.assertEqual(struct.pack('<f', result['reference_z']),
                                 struct.pack('<f', row['result']['reference_z']))

    def test_contact_zero_and_mode_choose_extra_offset(self):
        from reference.ground_response_pose import endpoint_output_stage
        args = self.args()
        r = endpoint_output_stage(**args)
        self.assertAlmostEqual(r['positions'][0][1], .15, places=6)
        self.assertAlmostEqual(r['positions'][1][1], .13, places=6)
        args['decay_mode'] = True
        self.assertEqual(endpoint_output_stage(**args)['offset_amounts'], (f32(.13),)*2)

    def test_blend_zero_keeps_previous_but_still_applies_offsets(self):
        from reference.ground_response_pose import endpoint_output_stage
        args = self.args(); args['blend'] = 0
        r = endpoint_output_stage(**args)
        self.assertEqual(r['smoothed'], args['previous'])
        self.assertEqual(r['positions'][0][2], 1)
        self.assertGreater(r['positions'][0][1], 0)

    def test_reference_adjustment_is_tenth_of_sum(self):
        from reference.ground_response_pose import endpoint_output_stage
        args = self.args(); args.update(offsets=(1,2),reference_z=5)
        self.assertAlmostEqual(endpoint_output_stage(**args)['reference_z'], 5.3, places=6)

    def test_rotation_changes_direction_without_normalization(self):
        from reference.ground_response_pose import endpoint_output_stage
        args = self.args(); args['rotations'] = ((1,0,0,0),(2,0,0,0))
        self.assertEqual(endpoint_output_stage(**args)['directions'], ((0.,-1.,0.,0.),(0.,-7.,0.,0.)))


class PoseContactTests(unittest.TestCase):
    def hit(self, **changes):
        h = dict(point=(0,0,1,0),normal=(0,0,1,0),hit_flags=0,
                 body_flags=0,hit_scalar=.5,override_allowed=True)
        h.update(changes);return h

    def call(self, hits):
        from reference.ground_response_pose import resolve_pose_contacts
        return resolve_pose_contacts((0,0,1,0),(9,9,9,0),(1,0,0,0),.3,hits)

    def test_original_ordered_hit_outputs(self):
        from reference.ground_response_pose import resolve_pose_contacts
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/pose_contact_validation.json').read_text())
        self.assertEqual(evidence['cases'],240)
        for i,row in enumerate(evidence['rows']):
            with self.subTest(case=i):
                actual=resolve_pose_contacts(**row['inputs']);expected=row['result']
                for key in ('point','normal'):
                    self.assertEqual(struct.pack('<4f',*actual[key]),struct.pack('<4f',*expected[key]))
                self.assertEqual(actual['accepted'],expected['accepted'])
                self.assertEqual(struct.pack('<f',actual['scalar']),struct.pack('<f',expected['scalar']))

    def test_exhausted_skipped_hits_keep_point_and_scalar_changes(self):
        r=self.call([self.hit(hit_flags=1<<15,body_flags=1<<15)])
        self.assertFalse(r['accepted']);self.assertEqual(r['scalar'],.5)
        self.assertEqual(r['point'],(0.,0.,.5,0.))
        self.assertEqual(r['normal'],(1.,0.,0.,0.))

    def test_capability_false_keeps_scalar_from_prior_skipped_hit(self):
        r=self.call([self.hit(hit_flags=1<<15,body_flags=1<<15),
                     self.hit(hit_scalar=.8,override_allowed=False)])
        self.assertTrue(r['accepted']);self.assertEqual(r['accepted_index'],1)
        self.assertEqual(r['scalar'],.5);self.assertAlmostEqual(r['point'][2],1.3,places=6)

    def test_threshold_and_bit24_change_adjusted_point(self):
        r=self.call([self.hit(hit_scalar=.05,hit_flags=1<<24)])
        self.assertEqual(r['scalar'],f32(.05));self.assertAlmostEqual(r['point'][2],.95,places=6)
        below=self.call([self.hit(hit_scalar=.049,hit_flags=1<<24)])
        self.assertEqual(below['scalar'],0.);self.assertEqual(below['point'][2],1.)

    def test_empty_hits_preserve_observations(self):
        r=self.call([])
        self.assertFalse(r['accepted']);self.assertEqual(r['point'],(9.,9.,9.,0.))
        self.assertEqual(r['scalar'],f32(.3))


class PoseSegmentTests(unittest.TestCase):
    def test_original_query_geometry(self):
        from reference.ground_response_pose import pose_contact_segment
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/pose_segment_validation.json').read_text())
        self.assertEqual(evidence['cases'],192)
        for row in evidence['rows']:
            actual=pose_contact_segment(**row['inputs'])
            for key in ('start','direction'):
                self.assertEqual(struct.pack('<4f',*actual[key]),struct.pack('<4f',*row['result'][key]))
            self.assertEqual(actual['range'],row['result']['range'])

    def test_zero_xyz_length_clears_direction_w(self):
        from reference.ground_response_pose import pose_contact_segment
        r=pose_contact_segment((1,2,3,4),(0,0,0,1))
        self.assertEqual(r['range'],0.)
        self.assertEqual(r['direction'],(0.,0.,0.,0.))
        self.assertNotEqual(r['start'][3],r['end'][3])

    def test_nonunit_axis_sets_range(self):
        from reference.ground_response_pose import pose_contact_segment
        r=pose_contact_segment((0,0,0,0),(0,0,2,0))
        self.assertEqual(r['range'],f32(4.8))
        self.assertEqual(r['direction'],(0.,0.,-1.,0.))

    def test_endpoint_rounding_can_collapse_probe(self):
        from reference.ground_response_pose import pose_contact_segment
        r=pose_contact_segment((1e8,1e8,1e8,0),(0,0,1,0))
        self.assertEqual(r['range'],0.)
        self.assertEqual(r['start'],r['end'])


class ContactDirectionTests(unittest.TestCase):
    def test_both_original_endpoint_blocks(self):
        from reference.ground_response_pose import orient_pose_contact_direction
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/pose_contact_direction_validation.json').read_text())
        self.assertEqual(evidence['cases'],384)
        for row in evidence['rows']:
            actual=orient_pose_contact_direction(**row['inputs'])
            self.assertEqual(struct.pack('<4f',*actual),struct.pack('<4f',*row['result']))

    def test_rejection_does_not_read_normal(self):
        from reference.ground_response_pose import orient_pose_contact_direction
        self.assertEqual(orient_pose_contact_direction((1,0,0,0),None,False),(1.,0.,0.,0.))

    def test_composed_contact_keeps_skipped_mutation_without_flipping(self):
        from reference.ground_response_pose import resolved_pose_contact
        r=resolved_pose_contact(endpoint=(0,0,0,0),axis=(0,0,1,0),
            initial_point=(0,0,0,0),initial_normal=(0,0,1,0),initial_scalar=.3,
            above_direction=(0,0,1,0),hits=[dict(point=(0,0,2,0),normal=(0,0,1,0),
                hit_flags=1<<15,body_flags=1<<15,hit_scalar=.5,override_allowed=True)])
        self.assertFalse(r['contact']['accepted'])
        self.assertEqual(r['contact']['point'],(0.,0.,1.5,0.))
        self.assertEqual(r['above_direction'],(0.,0.,1.,0.))

    def test_contact_to_tail_matches_explicit_composition(self):
        from reference.ground_response_pose import contacted_pose_tail, resolved_pose_tail
        root=Path(__file__).resolve().parents[1]
        request=json.loads((root/'engine/examples/pose_tail_probe.json').read_text())
        frame=request['frames'][0].copy()
        endpoints=frame.pop('endpoints');directions=frame.pop('above_directions');scalars=frame.pop('contact_scalars')
        frame['correction_previous']=request['initial_state']['correction']
        frame['endpoint_previous']=request['initial_state']['endpoints']
        contacts=[dict(endpoint=p,initial_point=p,initial_normal=(0,0,1,0),
                      initial_scalar=s,above_direction=d,hits=[])
                  for p,d,s in zip(endpoints,directions,scalars)]
        actual=contacted_pose_tail(contacts,**frame)
        expected=resolved_pose_tail(**frame,endpoints=endpoints,above_directions=directions,contact_scalars=scalars)
        self.assertEqual(actual['tail'],expected)


class PoseAdjustmentDirectionTests(unittest.TestCase):
    def test_original_direction_stores_for_both_endpoints(self):
        from reference.ground_response_pose import pose_adjustment_directions
        root=Path(__file__).resolve().parents[1]/'native/snow_host'
        for name in ('pose_directions_validation.json','pose_directions_second_validation.json'):
            evidence=json.loads((root/name).read_text())
            self.assertEqual(evidence['cases'],192)
            for row in evidence['rows']:
                seeds=iter(row['rsqrt_estimates'])
                actual=pose_adjustment_directions(**row['inputs'],reciprocal_sqrt=lambda n:next(seeds))
                for key in ('above_direction','below_direction'):
                    self.assertEqual(struct.pack('<4f',*actual[key]),struct.pack('<4f',*row['result'][key]))
                self.assertEqual(list(seeds),[])

    def test_tiny_vectors_are_preserved_without_seed(self):
        from reference.ground_response_pose import pose_adjustment_directions
        def forbidden(n):raise AssertionError('tiny branch must not require seed')
        r=pose_adjustment_directions((0,0,0,1),(0,0,1e-6,0),forbidden)
        self.assertEqual(r['above_direction'],(0.,f32(1e-6),0.,0.))
        self.assertLess(r['below_direction'][0],1e-10)

    def test_parallel_axis_leaves_both_directions_zero(self):
        from reference.ground_response_pose import pose_adjustment_directions
        r=pose_adjustment_directions((0,0,0,1),(1,0,0,0),None)
        self.assertEqual(r['above_direction'],(0.,)*4)
        self.assertEqual(r['below_direction'],(0.,)*4)

    def test_contact_flip_does_not_recompute_below_direction(self):
        from reference.ground_response_pose import pose_adjustment_directions,orient_pose_contact_direction
        r=pose_adjustment_directions((0,0,0,1),(0,0,1,0),lambda n:1.)
        self.assertEqual(r['above_direction'],(0.,1.,0.,0.))
        flipped=orient_pose_contact_direction(r['above_direction'],(0,1,0,0),True)
        self.assertEqual(flipped,(0.,-1.,0.,0.))
        self.assertEqual(r['below_direction'],(1.,0.,0.,0.))


class PoseAxisTests(unittest.TestCase):
    def test_original_axis_outputs_and_transform_routes(self):
        from reference.ground_response_pose import pose_contact_axis
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/pose_axis_validation.json').read_text())
        self.assertEqual(evidence['cases'],224)
        self.assertEqual({r['transform_route'] for r in evidence['rows']},{'inline','supplied_accessor'})
        for row in evidence['rows']:
            actual=pose_contact_axis(**row['inputs'])
            for key in ('axis','reference_position'):
                self.assertEqual(struct.pack('<4f',*actual[key]),struct.pack('<4f',*row['result'][key]))
            self.assertEqual(actual['length'],row['result']['length'])

    def test_threshold_inclusive_and_fallback_not_normalized(self):
        from reference.ground_response_pose import pose_contact_axis
        fallback=(0,0,7,4)
        r=pose_contact_axis((.01,0,0,999),(0,0,0,-999),fallback)
        self.assertTrue(r['used_fallback']);self.assertEqual(r['axis'],fallback)
        r=pose_contact_axis((.010001,0,0,999),(0,0,0,-999),fallback)
        self.assertFalse(r['used_fallback']);self.assertEqual(r['axis'],(1.,0.,0.,0.))

    def test_w_does_not_contribute_to_length(self):
        from reference.ground_response_pose import pose_contact_axis
        r=pose_contact_axis((1,2,3,900),(1,2,3,-900),(0,1,0,0))
        self.assertEqual(r['length'],0.)
        self.assertEqual(r['reference_position'],(1.,2.,3.,0.))


class EntityPoseTransformTests(unittest.TestCase):
    def test_original_full_entity_conversion(self):
        from reference.ground_response_pose import entity_pose_transform
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/entity_pose_validation.json').read_text())
        self.assertEqual(evidence['cases'],240)
        self.assertEqual({r['result']['branch'] for r in evidence['rows']},{'trace','x','y','z'})
        for row in evidence['rows']:
            actual=entity_pose_transform(**row['inputs'])
            for key in ('position_scalar','rotation'):
                self.assertEqual(struct.pack('<4f',*actual[key]),struct.pack('<4f',*row['result'][key]))

    def test_position_w_replaced_and_axis_ignores_scalar(self):
        from reference.ground_response_pose import entity_pose_transform,pose_contact_axis
        r=entity_pose_transform(((1,0,0,0),(0,1,0,0),(0,0,1,0)),(1,2,3,99),.25)
        self.assertEqual(r['position_scalar'],(1.,2.,3.,.25))
        self.assertEqual(r['rotation'],(0.,0.,0.,1.))
        axis=pose_contact_axis((1,2,4,8),r['position_scalar'],(0,1,0,0))
        self.assertEqual(axis['axis'],(0.,0.,1.,0.))

    def test_diagonal_ties_prefer_earlier_axis(self):
        from reference.ground_response_pose import entity_pose_transform
        r=entity_pose_transform(((0,0,0,0),(0,0,0,0),(0,0,0,0)),(0,0,0,0),1)
        self.assertEqual(r['branch'],'x')
        self.assertEqual(r['rotation'],(.5,0.,0.,0.))

    def test_no_implicit_rotation_normalization(self):
        from reference.ground_response_pose import entity_pose_transform
        r=entity_pose_transform(((2,0,0,0),(0,2,0,0),(0,0,2,0)),(0,0,0,0),1)
        self.assertGreater(r['rotation'][3],1.)


class ProviderPoseTests(unittest.TestCase):
    def test_original_reference_and_both_endpoint_branches(self):
        from reference.ground_response_pose import provider_pose_transform
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/provider_pose_validation.json').read_text())
        self.assertEqual(evidence['cases'],720)
        for row in evidence['rows']:
            actual=provider_pose_transform(**row['inputs'])
            for key in ('position','rotation'):
                self.assertEqual(struct.pack('<4f',*actual[key]),struct.pack('<4f',*row['result'][key]))

    def test_direct_mode_ignores_parent(self):
        from reference.ground_response_pose import provider_pose_transform
        r=provider_pose_transform((1,2,3,4),(0,0,0,2),None,None,True)
        self.assertEqual(r,{'position':(1.,2.,3.,4.),'rotation':(0.,0.,0.,2.)})

    def test_parent_w_is_not_position_scale(self):
        from reference.ground_response_pose import provider_pose_transform
        r=provider_pose_transform((1,2,3,9),(0,0,0,1),(10,20,30,4),(0,0,0,1),False)
        self.assertEqual(r['position'],(11.,22.,33.,4.))

    def test_nonunit_parent_not_normalized(self):
        from reference.ground_response_pose import provider_pose_transform
        r=provider_pose_transform((1,0,0,0),(0,0,0,1),(0,0,0,1),(0,0,0,2),False)
        self.assertEqual(r['position'],(7.,0.,0.,1.))
        self.assertEqual(r['rotation'],(0.,0.,0.,2.))


class EndpointOriginTests(unittest.TestCase):
    def test_both_original_endpoint_origins(self):
        from reference.ground_response_pose import pose_endpoint_origin
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/endpoint_origins_validation.json').read_text())
        self.assertEqual(evidence['endpoint_outputs'],384)
        for row in evidence['rows']:
            for arg,expected in zip(row['inputs'],row['result']):
                actual=pose_endpoint_origin(**arg)
                self.assertEqual(struct.pack('<4f',*actual['origin']),struct.pack('<4f',*expected['origin']))

    def test_identity_offset_and_masked_w(self):
        from reference.ground_response_pose import pose_endpoint_origin
        r=pose_endpoint_origin((0,0,1,99),(0,0,0,1))
        self.assertEqual(r['origin'],(0.,-f32(.13),1.,0.))


class PoseLookupTests(unittest.TestCase):
    def test_original_unsigned_lookup(self):
        from reference.ground_response_pose import pose_channel_index
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/pose_lookup_validation.json').read_text())
        self.assertEqual(evidence['cases'],512)
        for row in evidence['rows']:
            self.assertEqual(pose_channel_index(row['entries'],row['key']),row['index'])

    def test_duplicates_mask_and_missing_sentinel(self):
        from reference.ground_response_pose import pose_channel_index
        self.assertEqual(pose_channel_index([(8,0x10002),(8,3)],8),2)
        self.assertEqual(pose_channel_index([(8,0xffffffff)],8),65535)
        self.assertEqual(pose_channel_index(None,8),65535)
        self.assertEqual(pose_channel_index([],8),65535)
        with self.assertRaises(ValueError):pose_channel_index([(9,0),(8,0)],8)

    def test_safe_bank_rejects_missing_and_out_of_bounds(self):
        from reference.ground_response_pose import resolve_pose_channel
        for entries in ([],[(8,9)],[(8,65535)]):
            with self.assertRaises(ValueError):resolve_pose_channel({'entries':entries,'records':[]},8)


class ProviderCacheTests(unittest.TestCase):
    def test_original_cache_protocol(self):
        from reference.ground_response_pose import acquire_pose_provider
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/provider_cache_validation.json').read_text())
        self.assertEqual(evidence['cases'],108)
        for row in evidence['rows']:
            calls=[]
            def lookup():calls.append(1);return row['lookup_result']
            actual=acquire_pose_provider(**row['inputs'],lookup=lookup)
            self.assertEqual(actual,row['result']);self.assertEqual(len(calls),int(actual['refreshed']))

    def test_missing_result_is_cached_until_tag_changes(self):
        from reference.ground_response_pose import acquire_pose_provider
        def forbidden():raise AssertionError('cached miss must not query')
        self.assertIsNone(acquire_pose_provider(7,65535,7,['a'],forbidden)['component'])
        r=acquire_pose_provider(7,65535,8,['a'],lambda:0)
        self.assertEqual(r['component'],'a');self.assertEqual(r['cached_tag'],8)

    def test_force_lookup_and_tag_wrap(self):
        from reference.ground_response_pose import acquire_pose_provider
        self.assertTrue(acquire_pose_provider(7,65534,7,['a'],lambda:0)['refreshed'])
        self.assertTrue(acquire_pose_provider(255,0,0,['a'],lambda:None)['refreshed'])
        # Equality is all the native byte gate can observe, not elapsed changes.
        self.assertFalse(acquire_pose_provider(0,0,0,['a'],None)['refreshed'])

    def test_inspection_bounds_are_explicit(self):
        from reference.ground_response_pose import acquire_pose_provider
        with self.assertRaises(ValueError):acquire_pose_provider(0,3,0,['a'],None)
        with self.assertRaises(ValueError):acquire_pose_provider(0,65534,0,['a'],lambda:3)


class ComponentTypeSearchTests(unittest.TestCase):
    def test_original_candidate_slot_search(self):
        from reference.ground_response_pose import component_type_slot
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/component_type_search_validation.json').read_text())
        self.assertEqual(evidence['cases'],240)
        for row in evidence['rows']:
            self.assertEqual(component_type_slot(row['type_ranges'],row['requested_range']),row['result'])

    def test_containment_inclusive_and_missing(self):
        from reference.ground_response_pose import component_type_slot
        self.assertEqual(component_type_slot([(1,3),(5,8),(10,12)],(5,8)),1)
        self.assertEqual(component_type_slot([(1,3),(5,8),(10,12)],(4,9)),1)
        self.assertIsNone(component_type_slot([(1,3),(5,8)],(6,7)))
        self.assertIsNone(component_type_slot([],(0,65535)))

    def test_duplicate_range_and_unsigned_high_values(self):
        from reference.ground_response_pose import component_type_slot
        self.assertEqual(component_type_slot([(40000,50000),(40000,50000)],(40000,50000)),0)
        with self.assertRaises(ValueError):component_type_slot([(-1,2)],(0,2))


class BoundProviderSearchTests(unittest.TestCase):
    def test_original_getter_dispatch_through_all_bound_tables(self):
        from reference.ground_response_pose import acquire_pose_provider_by_ranges
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/provider_bound_search_validation.json').read_text())
        self.assertEqual(evidence['cases'],480)
        self.assertEqual({r['table_variant'] for r in evidence['rows']},{0,1,2})
        for row in evidence['rows']:
            components=list(range(len(row['type_ranges'])))
            result=acquire_pose_provider_by_ranges(255,65534,0,components,row['type_ranges'],row['requested_range'])
            self.assertEqual(result['component'],row['result'])
            self.assertEqual(result['cached_index'],65535 if row['result'] is None else row['result'])
            self.assertEqual(result['cached_tag'],0)

    def test_cached_path_does_not_read_descriptors(self):
        from reference.ground_response_pose import acquire_pose_provider_by_ranges
        result=acquire_pose_provider_by_ranges(1,0,1,['provider'],None,None)
        self.assertEqual(result['component'],'provider');self.assertFalse(result['refreshed'])
        with self.assertRaises(ValueError):
            acquire_pose_provider_by_ranges(1,65534,1,['provider'],[],(0,1))


class TypeNumberingTests(unittest.TestCase):
    def test_original_recursive_numbering(self):
        from reference.ground_response_pose import number_type_subtree
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/type_numbering_validation.json').read_text())
        self.assertEqual(evidence['cases'],128)
        for row in evidence['rows']:
            self.assertEqual(number_type_subtree(row['children'],row['root'],row['counter']),row['result'])

    def test_descendant_ranges_feed_type_search(self):
        from reference.ground_response_pose import number_type_subtree,component_type_slot
        r=number_type_subtree([[1,3],[2],[],[]],0,2)['ranges']
        self.assertEqual(r,[[3,10],[4,7],[5,6],[8,9]])
        self.assertEqual(component_type_slot([r[2],r[3]],r[1]),0)
        self.assertIsNone(component_type_slot([r[3]],r[1]))

    def test_uint16_wrap_and_invalid_tree(self):
        from reference.ground_response_pose import number_type_subtree
        self.assertEqual(number_type_subtree([[]],0,65535),{'ranges':[[0,1]],'counter':1})
        with self.assertRaises(ValueError):number_type_subtree([[1],[0]],0,0)
        with self.assertRaises(ValueError):number_type_subtree([[1,1],[]],0,0)


class TypeAssignmentTests(unittest.TestCase):
    def test_original_postsort_assignment(self):
        from reference.ground_response_pose import assign_type_ranges
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/type_assignment_validation.json').read_text())
        self.assertEqual(evidence['cases'],160)
        for row in evidence['rows']:
            self.assertEqual(assign_type_ranges(row['parents'],row['order'],row['root']),row['result'])

    def test_root_and_disconnected_fallback(self):
        from reference.ground_response_pose import assign_type_ranges
        result=assign_type_ranges([None,0,None,2],[0,2,1,3],0)
        self.assertEqual(result['ranges'],[[2,5],[3,4],[5,6],[7,8]])
        self.assertEqual(result['counter'],9)
        self.assertEqual(result['fallback_nodes'],[2,3])

    def test_repeated_parent_groups_retain_last_start(self):
        from reference.ground_response_pose import assign_type_ranges
        result=assign_type_ranges([None,0,1,0],[0,1,2,3],0)
        self.assertEqual(result['first_child'][0],3)
        self.assertEqual(result['fallback_nodes'],[1,2])
        with self.assertRaises(ValueError):assign_type_ranges([None,0],[0,0],0)


class TypeDescriptorOrderTests(unittest.TestCase):
    def test_original_sort_supported_domain_and_tie_boundary(self):
        from reference.ground_response_pose import type_descriptor_order
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/type_sort_validation.json').read_text())
        self.assertEqual(evidence['cases'],192)
        self.assertEqual(evidence['modeled_cases'],166)
        self.assertEqual(evidence['large_tie_reordered_cases'],26)
        for row in evidence['rows']:
            self.assertEqual(type_descriptor_order(row['keys']),row['order'])

    def test_lexicographic_unsigned_fields_and_small_tie_stability(self):
        from reference.ground_response_pose import type_descriptor_order
        self.assertEqual(type_descriptor_order([(2**31,0,0),(1,2,9),(1,1,99),(1,2,8),(1,2,8)]),[2,3,4,1,0])

    def test_equal_keys_supported_after_partition_recovery(self):
        from reference.ground_response_pose import type_descriptor_order
        self.assertEqual(type_descriptor_order([(0,0,0)]*32),list(range(32)))
        self.assertEqual(type_descriptor_order([(0,0,0)]*33),list(range(33)))


class TypePartitionTests(unittest.TestCase):
    def test_expanded_original_permutations(self):
        from reference.ground_response_pose import type_descriptor_order
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/type_sort_partition_validation.json').read_text())
        self.assertEqual(evidence['cases'],160)
        self.assertEqual(max(len(row['keys']) for row in evidence['rows']),1024)
        for row in evidence['rows']:
            self.assertEqual(type_descriptor_order(row['keys']),row['order'])


class TypeHeapTests(unittest.TestCase):
    def test_original_forced_and_mixed_heap_permutations(self):
        from reference.ground_response_pose import type_descriptor_order
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/type_sort_heap_validation.json').read_text())
        self.assertEqual(evidence['cases'],160)
        self.assertTrue(any(r['heap_calls'] and r['partition_budget']>0 for r in evidence['rows']))
        self.assertTrue(any(r['heap_calls'] and r['partition_budget']==0 for r in evidence['rows']))
        for row in evidence['rows']:
            self.assertEqual(type_descriptor_order(row['keys'],row['partition_budget']),row['order'])

    def test_heap_ties_are_not_stable_and_small_arrays_still_use_insertion(self):
        from reference.ground_response_pose import type_descriptor_order
        small=[(1,2,3)]*32
        self.assertEqual(type_descriptor_order(small,0),list(range(32)))
        large=[(1,2,3)]*33
        order=type_descriptor_order(large,0)
        self.assertEqual(sorted(order),list(range(33)))
        self.assertNotEqual(order,list(range(33)))
        with self.assertRaises(ValueError):type_descriptor_order(large,-1)


class TypePreparationTests(unittest.TestCase):
    def test_original_continuous_sort_and_assignment(self):
        from reference.ground_response_pose import prepare_type_ranges
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/type_preparation_validation.json').read_text())
        self.assertEqual(evidence['cases'],128)
        for row in evidence['rows']:
            self.assertEqual(prepare_type_ranges(row['parents'],row['keys'],row['root']),row['result'])

    def test_sort_keys_are_not_replaced_with_parent_order(self):
        from reference.ground_response_pose import prepare_type_ranges
        parents=[None,0,1,0]
        result=prepare_type_ranges(parents,[(0,0,i) for i in range(4)],0)
        self.assertEqual(result['order'],[0,1,2,3])
        self.assertEqual(result['fallback_nodes'],[1,2])
        with self.assertRaises(ValueError):prepare_type_ranges(parents,[(0,0,0)],0)


class TypeParentLinkTests(unittest.TestCase):
    def test_original_parent_link_loop(self):
        from reference.ground_response_pose import link_type_parents
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/type_parent_link_validation.json').read_text())
        self.assertEqual(evidence['cases'],128)
        for row in evidence['rows']:
            mapping=dict(row['lookup_entries'])
            self.assertEqual(link_type_parents(row['parent_keys'],row['previous_parents'],mapping.get),row['result'])

    def test_missing_parent_lookup_preserves_prior_link(self):
        from reference.ground_response_pose import link_type_parents
        self.assertEqual(link_type_parents([8,9],[1,None],{9:0}.get),[1,0])

    def test_parent_keys_group_siblings_before_numbering(self):
        from reference.ground_response_pose import link_type_parents,prepare_type_ranges
        parent_keys=[0,10,10,20]
        parents=link_type_parents(parent_keys,[None]*4,{10:0,20:1}.get)
        result=prepare_type_ranges(parents,[(k,32767,i) for i,k in enumerate(parent_keys)],0)
        self.assertEqual(result['fallback_nodes'],[])
        self.assertEqual(result['ranges'],[[2,9],[3,6],[7,8],[4,5]])


class CompactTypeRegistryTests(unittest.TestCase):
    def test_original_compact_and_null_lookup(self):
        from reference.ground_response_pose import compact_type_registry_index
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/compact_registry_validation.json').read_text())
        self.assertEqual(evidence['cases'],256)
        self.assertEqual({len(r['keys']) for r in evidence['rows'] if r['keys']},set(range(1,32)))
        for row in evidence['rows']:
            self.assertEqual(compact_type_registry_index(row['keys'],row['key']),row['index'])

    def test_joined_parent_pass_uses_compact_lookup(self):
        from reference.ground_response_pose import compact_type_registry_index,link_type_parents
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/type_parent_link_compact_validation.json').read_text())
        self.assertEqual(evidence['cases'],128)
        for row in evidence['rows']:
            mapping=dict(row['lookup_entries']);keys=sorted(mapping)
            def lookup(key):
                index=compact_type_registry_index(keys or None,key)
                return None if index is None else mapping[keys[index]]
            self.assertEqual(link_type_parents(row['parent_keys'],row['previous_parents'],lookup),row['result'])

    def test_unsigned_order_first_duplicate_and_validation(self):
        from reference.ground_response_pose import compact_type_registry_index as lookup
        self.assertEqual(lookup([0,2**63,2**63,2**64-1],2**63),1)
        self.assertIsNone(lookup([2,4],3))
        self.assertIsNone(lookup([2,4],5))
        self.assertIsNone(lookup(None,0))
        for keys,key in (([],0),([0]*32,0),([2,1],1),([-1],0),([True],1),([0],2**64),([0],False)):
            with self.assertRaises(ValueError):lookup(keys,key)


class CompactRegistryIterationTests(unittest.TestCase):
    def test_original_cursor_transitions(self):
        from reference.ground_response_pose import compact_type_registry_cursor
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/compact_iteration_validation.json').read_text())
        self.assertEqual(evidence['cases'],512)
        for row in evidence['rows']:
            self.assertEqual(compact_type_registry_cursor(row['keys'],row['key'],advance=row['advance']),row['result'])

    def test_exhaustion_wrap_and_duplicate_skip(self):
        from reference.ground_response_pose import compact_type_registry_cursor as cursor
        maximum=2**64-1
        self.assertEqual(cursor([0,0,4,maximum],0,advance=True),{'key':4,'index':2})
        self.assertEqual(cursor([0,4,maximum],maximum,advance=True),{'key':0,'index':None})
        self.assertEqual(cursor([0,4,maximum],0,advance=True),{'key':4,'index':1})
        self.assertEqual(cursor([4],7),{'key':8,'index':None})
        self.assertEqual(cursor(None,maximum,advance=True),{'key':maximum,'index':None})
        with self.assertRaises(ValueError):cursor([0],0,advance=1)

    def test_original_complete_parent_registry_loop(self):
        from reference.ground_response_pose import link_compact_type_registry
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/compact_parent_registry_validation.json').read_text())
        self.assertEqual(evidence['cases'],160)
        for row in evidence['rows']:
            self.assertEqual(link_compact_type_registry(row['registry_keys'],row['descriptor_indices'],row['parent_keys'],row['previous_parents']),row['result'])

    def test_registry_parent_links_feed_type_preparation(self):
        from reference.ground_response_pose import link_compact_type_registry,prepare_type_ranges
        parent_keys=[0,20,99,10]
        linked=link_compact_type_registry([0,10,20,30],[2,0,3,1],parent_keys,[None]*4)
        self.assertEqual(linked['parents'],[2,3,None,0])
        prepared=prepare_type_ranges(linked['parents'],[(k,32767,i) for i,k in enumerate(parent_keys)],2)
        self.assertEqual(prepared['fallback_nodes'],[])
        self.assertEqual(prepared['ranges'],[[3,8],[5,6],[2,9],[4,7]])

    def test_unregistered_and_duplicate_slots_preserve_links(self):
        from reference.ground_response_pose import link_compact_type_registry as link
        result=link([5,5,8],[0,1,2],[8,8,99,5],[None]*4)
        self.assertEqual(result['parents'],[2,None,None,None])
        self.assertEqual(result['visited_slots'],[0,2])
        for keys,values in (([1],[]),([1],[4]),(None,[0])):
            with self.assertRaises(ValueError):link(keys,values,[0],[None])


class SkeletonProviderBindingTests(unittest.TestCase):
    def test_native_provider_path_with_real_type_getters(self):
        from reference.ground_response_pose import acquire_pose_provider_by_ranges
        evidence=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/skeleton_provider_binding_validation.json').read_text())
        self.assertEqual(evidence['cases'],256)
        self.assertEqual(evidence['metadata_names'],['Component','SkeletonComponent'])
        self.assertTrue(evidence['base_constructor_direct_call_verified'])
        self.assertTrue(all(r['assigned_table'] and r['type_slot_bound'] for r in evidence['constructor_checks']))
        for row in evidence['rows']:
            result=acquire_pose_provider_by_ranges(row['cached_tag'],row['cached_index'],row['entity_tag'],list(range(len(row['component_types']))),row['type_ranges'],row['requested_range'])
            self.assertEqual(result,row['result'])
            self.assertEqual(row['observed_getter_types'][0],1)

    def test_cache_hit_can_skip_type_search(self):
        from reference.ground_response_pose import acquire_pose_provider_by_ranges
        result=acquire_pose_provider_by_ranges(7,0,7,['base','skeleton'],[[0,65535],[100,200]],[100,200])
        self.assertFalse(result['refreshed'])
        self.assertEqual(result['component'],'base')
        refreshed=acquire_pose_provider_by_ranges(6,0,7,['base','skeleton'],[[0,65535],[100,200]],[100,200])
        self.assertTrue(refreshed['refreshed'])
        self.assertEqual(refreshed['component'],'skeleton')
