import copy
import unittest

from engine import gameplay_jobs
from engine.runtime import Engine
from engine.trace import Trace
from engine.replay import record, replay


class GameplayJobTests(unittest.TestCase):
    def test_callbacks_are_separate_jobs_and_terminal_drains(self):
        visits = []
        context = {'value': 0}
        def phase(name):
            def execute(ctx):
                visits.append((name, ctx['value']))
                ctx['value'] += 1
            return execute
        trace = Trace(512)
        result = gameplay_jobs.run({name: phase(name) for name in gameplay_jobs.PHASES}, context, trace, tick=17)
        self.assertEqual(visits, list(zip(gameplay_jobs.PHASES, range(5))))
        self.assertEqual(result['jobs']['ready']['terminal_begins'], 1)
        self.assertFalse(result['queue'])
        self.assertFalse(result['dispatches'])
        self.assertTrue(all(job['executions'] == job['outstanding_dispatches'] == 0 for job in result['jobs'].values()))
        rows = trace.snapshot()['records']
        self.assertEqual([row['job'] for row in rows if row['job_event']=='mixed_dispatch_reserved'], list(gameplay_jobs.PHASES))
        self.assertEqual([row['job'] for row in rows if row['job_event']=='mixed_terminal_begin'], ['ready'])
        self.assertTrue(all(row['tick']==17 and row['kind']=='gameplay_job' for row in rows))

    def test_failure_stops_successors_and_is_not_a_commit(self):
        e = Engine({'execution_mode':'mixed'})
        before = e.snapshot()
        def fail(context):
            e.state['environment']['time_of_day'] = 99
            raise ValueError('environment failure')
        e._phase_environment = fail
        with self.assertRaisesRegex(ValueError, 'environment failure'):
            e.step()
        expected = copy.deepcopy(before);expected['paused'] = True
        self.assertEqual(e.state, expected)
        self.assertEqual(e.last_good, before)
        self.assertEqual(e.commands, [])
        rows = e.trace.snapshot()['records']
        self.assertEqual([row['job'] for row in rows if row.get('job_event')=='mixed_dispatch_reserved'], ['physics','environment'])
        self.assertTrue(any(row.get('job_event')=='mixed_handler_failed' for row in rows))
        self.assertFalse(any(row['kind']=='substep_committed' for row in rows))
        self.assertEqual(rows[-1]['kind'], 'substep_aborted')

    def test_graph_animation_and_rigid_physics_preserve_numerical_state(self):
        graph = {'schema_version':1,'root':'mix','nodes':{
            'idle':{'type':'clip','clip':'idle'},'bend':{'type':'clip','clip':'bend'},
            'mix':{'type':'blend','children':['idle','bend'],'weights':[1,{'input':'jump'}]}}}
        scenario = {'physics_mode':'rigid_cells','animation':{'graph':graph}}
        direct = Engine(scenario);mixed = Engine(dict(scenario, execution_mode='mixed'))
        for inputs in ({'steer':.5},{'jump':True,'flip':.2},{'brake':True}):
            for e in (direct,mixed):
                e.set_input(inputs);e.step(12)
            self.assertEqual(direct.state, mixed.state)
            self.assertEqual(direct.events, mixed.events)
        self.assertEqual(replay(record(mixed)).state_hash(), mixed.state_hash())

    def test_trace_surrounds_real_physics_and_animation_callbacks(self):
        e = Engine({'execution_mode':'mixed'});e.step()
        rows = e.trace.snapshot()['records']
        def index(kind, job=None):
            return next(i for i,row in enumerate(rows) if row.get('job_event',row['kind'])==kind and (job is None or row.get('job')==job))
        self.assertLess(index('mixed_receiver_enter','physics'), index('physics_complete'))
        self.assertLess(index('physics_complete'), index('mixed_receiver_return','physics'))
        self.assertLess(index('mixed_callback_enter','animation'), index('animation_complete'))
        self.assertLess(index('animation_complete'), index('mixed_callback_return','animation'))
        self.assertLess(index('mixed_terminal_begin','ready'), index('substep_committed'))

    def test_invalid_mode_load_preserves_engine(self):
        e = Engine();e.step();before=e.checkpoint()
        with self.assertRaises(ValueError):e.load_scenario({'execution_mode':'native'})
        self.assertEqual(e.checkpoint(),before)

    def test_incomplete_phase_map_rejected_before_callbacks(self):
        visits=[]
        with self.assertRaises(ValueError):
            gameplay_jobs.run({'physics':lambda ctx: visits.append(1)}, {}, Trace())
        self.assertEqual(visits,[])
