import copy
import unittest
from unittest.mock import patch
from engine.runtime import Engine
from engine.trace import Trace
from engine.trace_analysis import analyze
from engine import camera


class TraceAnalysisTests(unittest.TestCase):
    def test_actual_direct_and_mixed(self):
        for mode in ('direct','mixed'):
            e=Engine({'execution_mode':mode,'trace':{'capacity':2000}})
            e.advance(1/60)
            report=analyze(e.trace.snapshot())
            self.assertTrue(report['complete'])
            self.assertEqual(report['status'],'complete')
            self.assertEqual(report['anomalies'],[])
            self.assertEqual(len(report['substeps']),2)
            self.assertTrue(all(s['effective_outcome']=='committed' for s in report['substeps']))
            if mode=='mixed':
                self.assertTrue(all(p['worker_completed'] for p in report['substeps'][0]['phases'].values()))
            else:self.assertFalse(report['substeps'][0]['phases']['physics']['entered'])

    def test_outer_abort_invalidates_prior_commit_and_retry_distinct(self):
        e=Engine({'execution_mode':'mixed','trace':{'capacity':2000}})
        original=camera.update;calls=0
        def fail(*args):
            nonlocal calls
            calls+=1
            original(*args)
            if calls==2:raise ValueError('second substep')
        with patch('engine.runtime.camera.update',side_effect=fail):
            with self.assertRaises(ValueError):e.advance(1/60)
        e.advance(1/60)
        report=analyze(e.trace.snapshot())
        self.assertEqual(report['anomalies'],[])
        self.assertEqual([f['outcome'] for f in report['frames']],['aborted','committed'])
        self.assertEqual([s['local_outcome'] for s in report['substeps']],['committed','aborted','committed','committed'])
        self.assertEqual([s['effective_outcome'] for s in report['substeps']],['rolled_back','rolled_back','committed','committed'])
        self.assertEqual(len({s['invocation'] for s in report['substeps']}),4)
        self.assertEqual(report['substeps'][1]['failures'][0]['handler'],'camera')

    def test_drops_never_report_success_and_unknown_mode(self):
        e=Engine({'execution_mode':'mixed','trace':{'capacity':1}});e.step()
        report=analyze(e.trace.snapshot())
        self.assertFalse(report['complete']);self.assertEqual(report['status'],'incomplete')
        self.assertEqual(report['substeps'][0]['mode'],'direct_or_unobserved')
        self.assertEqual(report['substeps'][0]['effective_outcome'],'unverified_incomplete_trace')

    def test_terminal_is_not_worker_completion(self):
        t=Trace();t.emit('substep_enter',invocation=0,frame_invocation=None)
        t.emit('gameplay_job',invocation=0,frame_invocation=None,job_event='mixed_terminal_begin',job='ready')
        report=analyze(t.snapshot())
        self.assertEqual(report['status'],'incomplete');self.assertTrue(report['complete'])
        self.assertTrue(all(not p['worker_completed'] for p in report['substeps'][0]['phases'].values()))

    def test_invalid_envelope_and_identifiers(self):
        t=Trace();t.emit('substep_enter',invocation=True)
        with self.assertRaises(ValueError):analyze(t.snapshot())
        for bad in ({},None,{'capacity':1},dict(Trace().snapshot(),attempted=5)):
            with self.assertRaises(ValueError):analyze(bad)

    def test_out_of_order_and_commit_missing_receipts(self):
        t=Trace();t.emit('substep_enter',invocation=0)
        t.emit('gameplay_job',invocation=0,job_event='mixed_callback_return',job='animation')
        t.emit('substep_committed',invocation=0)
        report=analyze(t.snapshot())
        self.assertEqual(report['status'],'anomalous')
        messages=[a['message'] for a in report['anomalies']]
        self.assertIn('animation return without prior entry',messages)
        self.assertIn('commit before all worker completions',messages)

    def test_frame_pending_and_zero_tick_plan(self):
        e=Engine();e.advance(.001)
        report=analyze(e.trace.snapshot())
        self.assertEqual(report['frames'][0]['planned_count'],0)
        self.assertEqual(report['substeps'],[])
        self.assertEqual(report['status'],'complete')
        e=Engine();e.advance(1/120)
        snap=e.trace.snapshot();snap['records'].pop();snap['attempted']-=1
        report=analyze(snap)
        self.assertEqual(report['substeps'][0]['effective_outcome'],'pending_frame')
        self.assertEqual(report['status'],'incomplete')

    def test_input_not_mutated_and_standalone_aborted(self):
        e=Engine();e._phase_physics=lambda ctx:(_ for _ in ()).throw(ValueError('failed'))
        with self.assertRaises(ValueError):e.step()
        snap=e.trace.snapshot();before=copy.deepcopy(snap);report=analyze(snap)
        self.assertEqual(snap,before)
        self.assertEqual(report['substeps'][0]['effective_outcome'],'aborted')
        self.assertEqual(report['anomalies'],[])

    def test_next_phase_requires_previous_body_return(self):
        t=Trace();t.emit('substep_enter',invocation=0)
        for name in ('physics','environment'):
            t.emit('gameplay_job',invocation=0,job_event='mixed_callback_enter',job=name)
        t.emit('substep_aborted',invocation=0)
        report=analyze(t.snapshot())
        self.assertIn('phase entered before previous callback returned',[a['message'] for a in report['anomalies']])
