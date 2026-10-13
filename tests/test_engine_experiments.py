import unittest
from engine.experiments import run
from engine.runtime import Engine

class ExperimentTests(unittest.TestCase):
    def test_scripted_frames_and_input_generation(self):
        result=run(dict(schema_version=1,scenario={'scheduler':{'fixed_dt':.01}},commands=[
            {'op':'input','actions':{'steer':.5}},
            {'op':'advance','dt':.025},
            {'op':'assert','path':['tick'],'equals':2},
            {'op':'advance','dt':.015},
            {'op':'assert','path':['tick'],'equals':4}]))
        self.assertTrue(result['replay_equal']);self.assertTrue(result['trace']['complete'])
        entries=[r for r in result['trace']['records'] if r['kind']=='substep_enter']
        self.assertEqual(len(entries),4);self.assertEqual({r['input_generation'] for r in entries},{1})
        self.assertEqual([f['end_tick'] for f in result['frames']],[2,4])
    def test_checkpoint_continuation_and_trace(self):
        result=run(dict(schema_version=1,commands=[{'op':'step','count':3},{'op':'checkpoint','name':'a'},
            {'op':'step','count':2},{'op':'restore','name':'a'},{'op':'step','count':1}]))
        self.assertEqual(result['state']['tick'],4);self.assertTrue(result['replay_equal'])
        self.assertEqual(len([r for r in result['trace']['records'] if r['kind']=='substep_committed']),4)
    def test_trace_overflow_does_not_change_simulation(self):
        a=Engine({'trace':{'capacity':2}});b=Engine();a.step(8);b.step(8)
        self.assertEqual(a.snapshot(),b.snapshot());self.assertFalse(a.trace.snapshot()['complete'])
    def test_reads_do_not_advance_or_exchange(self):
        e=Engine();e.advance(.02);before=e.checkpoint()
        for _ in range(4):e.snapshot();e.trace.snapshot();e.state_hash()
        self.assertEqual(before,e.checkpoint())
    def test_bad_assertion_fails_loudly(self):
        with self.assertRaises(AssertionError):run(dict(schema_version=1,commands=[{'op':'assert','path':['tick'],'equals':1}]))
    def test_aborted_frame_is_marked_in_trace(self):
        e=Engine({'scheduler':{'fixed_dt':.1}})
        with self.assertRaises(ValueError):e.advance(.1)
        self.assertEqual(e.state['tick'],0)
        self.assertEqual(e.trace.records[-1]['kind'],'frame_aborted')
