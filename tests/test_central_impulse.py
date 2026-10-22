import unittest
from reference.central_impulse import central_impulse, coupled_delta_velocity_impulses


class CentralImpulseTests(unittest.TestCase):
    def test_preserves_spin_and_adds_linear_momentum(self):
        r = central_impulse((4, -2, 1), (3, -4, 5), (2, 6, -4), .5)
        self.assertEqual(r['linear'], (5, 1, -1))
        self.assertEqual(r['angular'], (3, -4, 5))

    def test_gate_matrix(self):
        for kind in (0, 1, 2, 15, 18):
            for flags in (0, 8, 9, 255):
                for force in (False, True):
                    r = central_impulse((1, 2, 3), (4, 5, 6), (2, 4, 6), .5, kind=kind, flags=flags, force=force)
                    entered = kind & 15 != 2 or force
                    writes = entered and not flags & 8
                    self.assertEqual(r['linear'], (2, 4, 6) if writes else (1, 2, 3))
                    self.assertEqual(r['angular'], (4, 5, 6))
                    self.assertEqual(r['post_dispatch_requested'], entered and force)

    def test_zero_inverse_mass(self):
        r = central_impulse((1, 2, 3), (4, 5, 6), (100, 200, 300), 0, force=True)
        self.assertEqual(r['linear'], (1, 2, 3))
        self.assertTrue(r['post_dispatch_requested'])

    def test_equal_delta_v_for_unequal_bodies(self):
        impulses = coupled_delta_velocity_impulses((2, -1, .5), (.25, .05))
        for im, impulse in zip((.25, .05), impulses):
            r = central_impulse((0, 0, 0), (3, 4, 5), impulse, im)
            for got, expected in zip(r['linear'], (2, -1, .5)):
                self.assertAlmostEqual(got, expected, places=6)
            self.assertEqual(r['angular'], (3, 4, 5))

    def test_validation(self):
        for masses in ((), (0,), (-1,), (float('nan'),)):
            with self.assertRaises(ValueError):
                coupled_delta_velocity_impulses((1, 2, 3), masses)
        with self.assertRaises(ValueError):
            central_impulse((0, 0, 0), (0, 0, 0), (float('inf'), 0, 0), 1)


class PendingImpulseTests(unittest.TestCase):
    def body(self, im, flags=0):
        return dict(linear=(1, 2, 3), angular=(4, 5, 6), inverse_mass=im, flags=flags)

    def test_threshold_retains_small_pending(self):
        from reference.central_impulse import consume_pending_impulse, f32
        p = (f32(1e-5), -f32(1e-5), 0, 0)
        r = consume_pending_impulse(p, [self.body(.25)])
        self.assertFalse(r['consumed'])
        self.assertEqual(r['pending'], p)

    def test_fourth_lane_triggers_dispatch_but_not_momentum(self):
        from reference.central_impulse import consume_pending_impulse
        r = consume_pending_impulse((0, 0, 0, .01), [self.body(.25)])
        self.assertTrue(r['consumed'])
        self.assertEqual(r['submissions'][0]['linear'], (1, 2, 3))
        self.assertTrue(r['submissions'][0]['post_dispatch_requested'])
        self.assertEqual(r['pending'], (0, 0, 0, 0))

    def test_same_impulse_unequal_velocity_changes(self):
        from reference.central_impulse import consume_pending_impulse
        r = consume_pending_impulse((4, 0, 0, 0), [self.body(.25), self.body(.5)])
        self.assertEqual([s['linear'][0] for s in r['submissions']], [2, 3])
        self.assertTrue(all(s['angular'] == (4, 5, 6) for s in r['submissions']))

    def test_suppression_does_not_retain_pending(self):
        from reference.central_impulse import consume_pending_impulse
        r = consume_pending_impulse((4, 0, 0, 0), [self.body(.25, 8)])
        self.assertFalse(r['submissions'][0]['velocity_write_enabled'])
        self.assertTrue(r['consumed'])
        self.assertEqual(r['pending'], (0, 0, 0, 0))


class QueuedImpulseTests(unittest.TestCase):
    def test_accumulation_and_clear(self):
        from reference.central_impulse import queue_pending_impulse, clear_pending_impulse
        p = queue_pending_impulse((1, 2, 3, 4), (4, -2, 1, -4))
        self.assertEqual(p, (5, 0, 4, 0))
        self.assertEqual(clear_pending_impulse(p), (0, 0, 0, 0))

    def test_missing_runtime_does_not_read_input(self):
        from reference.central_impulse import queue_pending_impulse, clear_pending_impulse
        self.assertIsNone(queue_pending_impulse(None, object()))
        self.assertIsNone(clear_pending_impulse(None))

    def test_queue_to_consumer(self):
        from reference.central_impulse import queue_pending_impulse, consume_pending_impulse
        p = queue_pending_impulse((0, 0, 0, 0), (4, 0, 0, 0))
        r = consume_pending_impulse(p, [dict(linear=(1, 2, 3), angular=(4, 5, 6), inverse_mass=.25)])
        self.assertEqual(r['submissions'][0]['linear'], (2, 2, 3))
        self.assertEqual(r['submissions'][0]['angular'], (4, 5, 6))
        self.assertEqual(r['pending'], (0, 0, 0, 0))


class ProducerRouteTests(unittest.TestCase):
    def test_matches_native_dispatch_observations(self):
        import json
        from pathlib import Path
        from reference.central_impulse import queue_producer_route_selected
        fixture = Path(__file__).resolve().parents[1] / 'native/snow_host/impulse_route_validation.json'
        rows = json.loads(fixture.read_text())['rows']
        self.assertEqual(len(rows), 72)
        for row in rows:
            with self.subTest(row=row):
                self.assertEqual(queue_producer_route_selected(row['state'], row['variant']), row['producer_route_selected'])


class PendingPrepassTests(unittest.TestCase):
    def test_matches_original_instruction_observations(self):
        import json
        from pathlib import Path
        from reference.central_impulse import pending_consumer_prepass
        evidence = Path(__file__).resolve().parents[1] / 'native/snow_host/pending_prepass_validation.json'
        rows = json.loads(evidence.read_text())['rows']
        self.assertEqual(len(rows), 432)
        for row in rows:
            result = pending_consumer_prepass(*(row[k] for k in
                ('enabled_byte','blocked_byte','counter','timer_a','timer_b','helper_gain')))
            self.assertEqual(result['optional_helper_requested'], row['helper_requested'])
            self.assertEqual(result['counter_after'], row['counter_after'])
            self.assertTrue(result['reaches_pending_threshold_on_normal_return'])

    def test_helper_gate_does_not_block_pending_consumption(self):
        from reference.central_impulse import pending_consumer_prepass, consume_pending_impulse
        pre = pending_consumer_prepass(0, 1, 99, 10, 10, 0)
        self.assertFalse(pre['optional_helper_requested'])
        self.assertTrue(pre['reaches_pending_threshold_on_normal_return'])
        result = consume_pending_impulse((4,0,0,0), [dict(linear=(0,0,0),angular=(1,2,3),inverse_mass=.25)])
        self.assertEqual(result['submissions'][0]['linear'], (1,0,0))
        self.assertEqual(result['submissions'][0]['angular'], (1,2,3))

    def test_counter_wrap_and_validation(self):
        from reference.central_impulse import pending_consumer_prepass
        self.assertEqual(pending_consumer_prepass(1,0,-2147483648,0,0,1)['counter_after'],2147483647)
        for values in ((256,0,0,0,0,1),(1,0,2147483648,0,0,1),(1,0,0,float('nan'),0,1)):
            with self.assertRaises(ValueError):pending_consumer_prepass(*values)


class HelperImpulseTests(unittest.TestCase):
    def test_native_tail_observations(self):
        import json
        from pathlib import Path
        from reference.central_impulse import helper_direct_impulses
        p=Path(__file__).resolve().parents[1]/'native/snow_host/helper_impulse_validation.json'
        rows=json.loads(p.read_text())['rows']
        self.assertEqual(len(rows),192)
        for r in rows:
            actual=helper_direct_impulses(r['scale'],r['dt'],(1,-.5,2),r['descriptor_scale'],
                                         r['combined_mass'],20,r['mask_eligible'],r['override_byte'])
            self.assertEqual(json.loads(json.dumps(actual)),{'submitted':r['submitted'],'submissions':r['submissions']})

    def test_zero_dt_still_submits_and_negative_main_share_not_clamped(self):
        from reference.central_impulse import helper_direct_impulses
        r=helper_direct_impulses(-1,0,(1,0,0),1,5,20,True,0)
        self.assertTrue(r['submitted'])
        self.assertEqual([s['body'] for s in r['submissions']],['rider','main'])
        self.assertTrue(all(s['impulse']==(0,0,0) for s in r['submissions']))
        r=helper_direct_impulses(-1,1,(1,0,0),1,5,20,True,0)
        self.assertEqual(r['submissions'][0]['impulse'],(-20,0,0))
        self.assertEqual(r['submissions'][1]['impulse'],(15,0,0))

    def test_threshold_and_mask_override(self):
        from reference.central_impulse import helper_direct_impulses
        self.assertFalse(helper_direct_impulses(-.1,1,(1,0,0),1,80,20,True,1)['submitted'])
        self.assertFalse(helper_direct_impulses(-1,1,(1,0,0),1,80,20,False,0)['submitted'])
        self.assertTrue(helper_direct_impulses(-1,1,(1,0,0),1,80,20,False,1)['submitted'])


class HelperForceScaleTests(unittest.TestCase):
    def test_original_instruction_cases(self):
        import json
        from pathlib import Path
        from reference.central_impulse import helper_force_scale
        rows=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/helper_force_scale_validation.json').read_text())['rows']
        self.assertEqual(len(rows),280)
        for row in rows:
            inputs={k:v for k,v in row.items() if k not in ('eligible','scale')}
            result=helper_force_scale(**inputs)
            self.assertEqual(result['eligible'],row['eligible'])
            self.assertEqual(result['scale'],row['scale'])

    def test_triangular_speed_and_overrides(self):
        from reference.central_impulse import helper_force_scale
        def run(speed, a=0, b=0):
            return helper_force_scale(speed,1,1,1,0,2,3,0,1,a,b,2)
        self.assertEqual(run(7)['speed_factor'],14)
        self.assertEqual(run(15)['speed_factor'],30)
        self.assertEqual(run(20)['speed_factor'],20)
        self.assertFalse(run(30)['eligible'])
        self.assertEqual(run(31,b=1)['speed_factor'],30)
        self.assertEqual(run(31,a=1)['scale'],-60)

    def test_scale_composes_with_direct_tail(self):
        from reference.central_impulse import helper_force_scale, helper_direct_impulses
        scale=helper_force_scale(15,1,1,1,0,2,3,0,1,0,0,1)['scale']
        result=helper_direct_impulses(scale,1/60,(0,0,1),1,80,20,True,0)
        self.assertTrue(result['submitted'])
        self.assertEqual(result['submissions'][0]['impulse'],(0,0,-10))
        self.assertEqual(result['submissions'][1]['impulse'],(0,0,-30))

    def test_zero_denominator_checked_only_on_active_sqrt_branch(self):
        from reference.central_impulse import helper_force_scale
        self.assertTrue(helper_force_scale(15,1,1,1,0,0,3,0,1,0,0,1)['eligible'])
        with self.assertRaises(ValueError):
            helper_force_scale(15,1,1,1,0,0,3,1,1,0,0,1)


class HelperGeometryTests(unittest.TestCase):
    def test_original_instruction_geometry_with_captured_rsqrt_estimates(self):
        import json
        from pathlib import Path
        from reference.central_impulse import helper_force_geometry
        rows=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/helper_geometry_validation.json').read_text())['rows']
        self.assertEqual(len(rows),112)
        for r in rows:
            seeds=iter(r['rsqrt_seeds'])
            got=helper_force_geometry(r['direction_input'],r['reference_axis'],r['source_vector'],lambda n:next(seeds))
            self.assertEqual(json.loads(json.dumps(got)),r['result'])
            self.assertIsNone(next(seeds,None))

    def test_fallback_and_dot_gate(self):
        from reference.central_impulse import helper_force_geometry
        got=helper_force_geometry((0,0,1),(0,0,-.6),(0,0,0),lambda n:1)
        self.assertEqual(got['direction'],(0,0,1))
        self.assertEqual(got['alignment'],0)
        self.assertFalse(got['eligible'])
        self.assertEqual(got['branch'],'world_z_fallback')

    def test_zero_input_policy(self):
        from reference.central_impulse import helper_force_geometry
        with self.assertRaises(ValueError):
            helper_force_geometry((0,0,0),(0,0,1),(1,0,0),lambda n:1)


class HelperEntryTests(unittest.TestCase):
    def test_original_entry_branches(self):
        import json
        from pathlib import Path
        from reference.central_impulse import helper_entry_eligible
        rows=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/helper_entry_validation.json').read_text())['rows']
        self.assertEqual(len(rows),144)
        for row in rows:
            self.assertEqual(helper_entry_eligible(**{k:v for k,v in row.items() if k!='eligible'}),row['eligible'])


class HelperFilterTests(unittest.TestCase):
    def evidence(self):
        import json
        from pathlib import Path
        return json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/helper_filter_validation.json').read_text())

    def test_native_filter_cases_and_publication(self):
        import json
        from reference.central_impulse import helper_response_filter
        rows=self.evidence()['rows']
        self.assertEqual(len(rows),675)
        for row in rows:
            got=helper_response_filter(**{k:v for k,v in row.items() if k!='result'})
            self.assertEqual(json.loads(json.dumps(got)),row['result'])

    def test_native_pulse_and_recovery_trajectory(self):
        from reference.central_impulse import helper_response_filter
        trajectory=self.evidence()['trajectory'];rate,displacement=trajectory['initial']
        self.assertEqual(len(trajectory['rows']),180)
        for row in trajectory['rows']:
            got=helper_response_filter(rate,displacement,row['acceleration'],trajectory['axis'],trajectory['dt'])
            rate,displacement=got['rate'],got['displacement']
            self.assertEqual((rate,displacement),(row['rate'],row['displacement']))

    def test_native_history_and_timestep_policy(self):
        import json
        from reference.central_impulse import helper_velocity_history
        rows=self.evidence()['history']['rows'];self.assertEqual(len(rows),12)
        for row in rows:
            got=helper_velocity_history(row['previous_velocity'],row['current_velocity'],row['dt'])
            self.assertEqual(json.loads(json.dumps(got)),row['result'])
        with self.assertRaises(ValueError):helper_velocity_history((0,0,0),(1,2,3),0)

    def test_drive_threshold_and_exact_bounds(self):
        from reference.central_impulse import helper_response_filter,f32
        self.assertEqual(helper_response_filter(0,0,(0,0,9.99),(0,0,1),0)['drive'],0)
        self.assertEqual(helper_response_filter(0,0,(0,0,10),(0,0,1),0)['drive'],10)
        exact=helper_response_filter(1,.8,(0,0,0),(0,0,1),0)
        self.assertFalse(exact['clipped']);self.assertEqual(exact['rate'],1)
        over=helper_response_filter(1,.81,(0,0,0),(0,0,1),0)
        self.assertTrue(over['clipped']);self.assertEqual(over['published'],(0,f32(.8)))
