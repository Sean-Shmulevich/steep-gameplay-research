import unittest

from engine.runtime import Engine
from engine.gameplay_jobs import PHASES
from engine.trace_analysis import analyze


class PhaseCaptureTests(unittest.TestCase):
    def test_capture_preserves_physics_and_links_input_to_pose(self):
        for mode in ('direct', 'mixed'):
            with self.subTest(mode=mode):
                plain = Engine({'execution_mode':mode})
                observed = Engine({'execution_mode':mode,
                                   'trace':{'capture_phase_state':True}})
                for engine in (plain, observed):
                    engine.set_input({'steer':.4, 'jump':True})
                    engine.step(1)
                self.assertEqual(plain.state_hash(), observed.state_hash())
                trace = observed.trace.snapshot()
                rows = [r for r in trace['records'] if r['kind']=='phase_state']
                self.assertEqual([(r['phase'],r['boundary']) for r in rows],
                                 [(p,b) for p in PHASES for b in ('enter','return')])
                self.assertTrue(all(r['input_generation']==1 for r in rows))
                self.assertEqual(len({r['invocation'] for r in rows}),1)
                self.assertEqual(rows[1]['state']['body'],rows[6]['state']['body'])
                self.assertEqual(rows[7]['state']['pose'],observed.state['pose'])
                rows[7]['state']['body']['position'][0]=999
                self.assertNotEqual(observed.state['body']['position'][0],999)
                self.assertEqual(analyze(trace)['anomalies'],[])

    def test_failed_phase_has_no_successful_return_observation(self):
        engine = Engine({'execution_mode':'mixed','trace':{'capture_phase_state':True}})
        def fail(context):
            engine.state['camera']['transient']=True
            raise ValueError('synthetic camera failure')
        engine._phase_camera=fail
        with self.assertRaises(ValueError):
            engine.step(1)
        trace=engine.trace.snapshot()
        camera=[r for r in trace['records'] if r['kind']=='phase_state' and r['phase']=='camera']
        self.assertEqual([r['boundary'] for r in camera],['enter'])
        self.assertNotIn('transient',engine.state['camera'])
        self.assertEqual(engine.state['tick'],0)
        self.assertTrue(any(r['kind']=='substep_aborted' for r in trace['records']))

    def test_capture_budget_and_configuration_are_explicit(self):
        engine=Engine({'trace':{'capacity':5,'capture_phase_state':True}})
        engine.step(1)
        trace=engine.trace.snapshot()
        self.assertFalse(trace['complete'])
        self.assertGreater(trace['dropped'],0)
        with self.assertRaises(ValueError):
            Engine({'trace':{'capture_phase_state':1}})
