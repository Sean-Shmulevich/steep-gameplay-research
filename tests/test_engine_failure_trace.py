import unittest
from engine.control import SchedulerController
from engine.runtime import Engine
from engine.trace import Trace


class FailureTraceTests(unittest.TestCase):
    def test_rollback_keeps_failure_pose_evidence_separate(self):
        engine=Engine({'trace':{'capacity':1000,'capture_phase_state':True}})
        controller=SchedulerController(engine=engine)
        token=controller.pause()
        before=controller.snapshot()
        def fail(context):
            raise ValueError('camera failure after animation')
        engine._phase_camera=fail
        with self.assertRaises(ValueError):
            controller.step_once(token, {'steer':.5})
        after=controller.snapshot()
        self.assertEqual(after['state'],before['state'])
        self.assertEqual(after['trace'],before['trace'])
        incident=after['incidents'][-1]
        excerpt=incident['failure_trace']
        self.assertTrue(excerpt['complete'])
        self.assertTrue(any(r['kind']=='phase_state' and r['phase']=='animation'
                            and r['boundary']=='return' for r in excerpt['records']))
        self.assertTrue(any(r['kind']=='substep_aborted' for r in excerpt['records']))
        self.assertEqual(incident['generation_before_failure'],0)
        with self.assertRaises(ValueError):
            controller.step_once(token)
        checkpoint=controller.checkpoint()
        other=SchedulerController()
        other.restore(checkpoint)
        self.assertEqual(other.snapshot()['incidents'],after['incidents'])

    def test_excerpt_distinguishes_capacity_loss_from_tail_trimming(self):
        trace=Trace(5)
        for i in range(8):trace.emit('synthetic',value=i)
        excerpt=trace.excerpt_since(2,limit=2)
        self.assertEqual([r['sequence'] for r in excerpt['records']],[3,4])
        self.assertEqual(excerpt['attempted'],6)
        self.assertEqual(excerpt['dropped_at_capture'],3)
        self.assertEqual(excerpt['omitted_by_excerpt'],1)
        self.assertFalse(excerpt['complete'])
        excerpt['records'][0]['value']=999
        self.assertEqual(trace.records[3]['value'],3)

    def test_diagnostic_failure_cannot_block_state_rollback(self):
        engine=Engine()
        controller=SchedulerController(engine=engine)
        token=controller.pause()
        def fail(context):
            engine.state['body']['position'][0]=999
            raise ValueError('original execution failure')
        def failed_capture(*args,**kwargs):
            raise RuntimeError('diagnostic failure')
        engine._phase_physics=fail
        engine.trace.excerpt_since=failed_capture
        with self.assertRaisesRegex(ValueError,'original execution failure'):
            controller.step_once(token)
        snapshot=controller.snapshot()
        self.assertNotEqual(snapshot['state']['body']['position'][0],999)
        self.assertEqual(snapshot['incidents'][-1]['failure_trace'],
                         dict(complete=False,capture_error='RuntimeError'))
