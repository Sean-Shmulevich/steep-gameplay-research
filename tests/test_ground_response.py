import json
import math
import unittest
from pathlib import Path
from reference.runtime_curve import evaluate
from reference.ground_response import HelperState, update


class RuntimeCurveTests(unittest.TestCase):
    def test_original_curve_cases(self):
        rows=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/runtime_curve_validation.json').read_text())['rows']
        self.assertEqual(len(rows),180)
        for r in rows:self.assertEqual(evaluate(r['value'],r['start'],r['index_scale'],r['segments']),r['result'])

    def test_invalid_table_contract(self):
        for scale,table in ((0,[(1,0)]),(1,[])):
            with self.assertRaises(ValueError):evaluate(0,0,scale,table)


class ComposedHelperTests(unittest.TestCase):
    def setUp(self):
        self.state=HelperState((9,9,9),(0,0,0),0,0)
        self.observation=dict(current_velocity=(0,0,.5),dt=1/60,contact_fraction=1,auxiliary_scalar=0,
                              direction_input=(1,0,1),reference_axis=(0,0,1),source_vector=(1,0,0),
                              curve_a_input=.4,curve_b_input=.5)
        self.force=dict(speed_scalar=15,measure=0,measure_limit=2,response_strength=3,activity_scalar=0,
                        contact_time=1,override_a=0,override_b=0,override_gain=1)
        self.submission=dict(descriptor_scale=1,combined_mass=80,rider_mass=20,mask_eligible=True)
        self.calls=[]
        def curve(name):
            def call(value):
                self.calls.append(name)
                return evaluate(value,0,1,[(0,1)])
            return call
        self.curves={name:curve(name) for name in ('entry','a','b')}

    def run_update(self, observation=None):
        # Derived seed policy for integration tests only, not native RSQRT equivalence.
        return update(self.state,self.observation if observation is None else observation,self.curves,
                      lambda n:1/math.sqrt(n),force=self.force,submission=self.submission)

    def test_full_stage_order_history_and_publication(self):
        result=self.run_update()
        self.assertEqual(self.calls,['entry','a','b'])
        self.assertEqual([s['body'] for s in result['submissions']],['rider','main'])
        self.assertEqual(result['state'].previous_velocity,(0,0,0))
        self.assertEqual(result['state'].current_velocity,(0,0,.5))
        self.assertEqual(result['publication'],(result['state'].rate,result['state'].displacement))
        self.assertGreater(result['filter']['drive'],10)
        self.assertEqual(self.state.current_velocity,(0,0,0))

    def test_entry_rejection_does_not_read_history_or_publish(self):
        self.curves['entry']=lambda speed:0
        result=self.run_update(dict(contact_fraction=0,auxiliary_scalar=1))
        self.assertIs(result['state'],self.state)
        self.assertIsNone(result['publication'])
        self.assertEqual(result['submissions'],())

    def test_geometric_and_speed_rejection_still_update_filter(self):
        self.observation['direction_input']=(0,0,-1)
        result=self.run_update();self.assertEqual(self.calls,['entry'])
        self.assertEqual(result['submissions'],());self.assertIsNotNone(result['publication'])
        self.observation['direction_input']=(1,0,1);self.force['speed_scalar']=30;self.calls.clear()
        result=self.run_update();self.assertEqual(self.calls,['entry'])
        self.assertEqual(result['submissions'],());self.assertIsNotNone(result['publication'])

    def test_nonpositive_factor_follows_curve_calls(self):
        self.force['speed_scalar']=0
        result=self.run_update()
        self.assertEqual(self.calls,['entry','a','b'])
        self.assertEqual(result['submissions'],())
        self.assertIsNotNone(result['publication'])

    def test_complete_original_helper_observations(self):
        from dataclasses import asdict
        rows=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/helper_complete_validation.json').read_text())['rows']
        self.assertEqual(len(rows),32)
        for r in rows:
            self.setUp()
            self.observation['direction_input']=r['direction_input']
            self.force['speed_scalar']=r['speed_scalar'];self.force['override_a']=r['override_a']
            self.submission['mask_eligible']=r['mask_eligible']
            def entry(value):
                self.calls.append('entry');return evaluate(value,0,1,[(0,r['entry_curve'])])
            self.curves['entry']=entry
            seeds=iter(r['rsqrt_seeds'])
            result=update(self.state,self.observation,self.curves,lambda n:next(seeds),force=self.force,submission=self.submission)
            self.assertEqual(self.calls,r['curve_calls'])
            self.assertEqual(json.loads(json.dumps(asdict(result['state']))),r['state'])
            self.assertEqual(json.loads(json.dumps(result['submissions'])),r['submissions'])
            self.assertEqual(json.loads(json.dumps(result['publication'])),r['publication'])
            self.assertEqual(result['entered'],r['entered'])
            self.assertIsNone(next(seeds,None))


class CurveBuilderTests(unittest.TestCase):
    def test_original_builder_and_evaluator_cases(self):
        from reference.runtime_curve import compile_samples
        rows=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/runtime_curve_builder_validation.json').read_text())['rows']
        self.assertEqual(len(rows),18)
        for row in rows:
            table=compile_samples(row['domain'],row['samples'],zero_origin=row['zero_origin'])
            self.assertEqual(json.loads(json.dumps(table)),row['compiled'])
            for e in row['evaluations']:self.assertEqual(evaluate(e['value'],**table),e['result'])

    def test_invalid_domain_and_sample_count(self):
        from reference.runtime_curve import compile_samples
        for domain,samples in (((1,1),(0,1)),((2,1),(0,1)),((0,1),(0,))):
            with self.assertRaises(ValueError):compile_samples(domain,samples)

    def test_profile_adapter_uses_distinct_roles(self):
        from reference.ground_response import compile_curves
        # Synthetic settings, no game tuning payload.
        settings={name:{'domain':[0,1],'$array':[value,value]} for name,value in
                  (('forceSpeedCurve',.5),('legCoilCurve',2),('forceDepthCurve',3))}
        curves=compile_curves(settings)
        self.assertEqual(curves['entry'](.2),.5)
        self.assertEqual(curves['a'](.2),2)
        self.assertEqual(curves['b'](.2),3)
        with self.assertRaises(KeyError):compile_curves({})
