import unittest
from unittest.mock import patch
from engine.control import SchedulerController
from engine.trace import Trace


class LightObservationTests(unittest.TestCase):
    def test_summary_avoids_trace_copy_and_reports_loss(self):
        c=SchedulerController({'trace':{'capacity':1}})
        c.submit_frame(.02,include_trace=False)
        with patch.object(Trace,'snapshot',side_effect=AssertionError('full copy')):
            observed=c.snapshot(include_trace=False)
        self.assertNotIn('trace',observed)
        self.assertFalse(observed['trace_summary']['records_included'])
        self.assertFalse(observed['trace_summary']['complete'])
        observed['state']['body']['velocity'][0]=999
        full=c.snapshot()
        self.assertNotEqual(full['state']['body']['velocity'][0],999)
        self.assertEqual(observed['trace_summary']['attempted'],full['trace']['attempted'])
        self.assertEqual(observed['trace_summary']['dropped'],full['trace']['dropped'])

    def test_step_observation_does_not_change_replay_or_trace(self):
        light=SchedulerController();full=SchedulerController()
        lt=light.pause();ft=full.pause()
        for _ in range(3):
            a=light.step_frame_once(lt,.02,{'steer':.3},include_trace=False)
            b=full.step_frame_once(ft,.02,{'steer':.3})
            self.assertEqual(a['state'],b['state'])
        self.assertEqual(light.export_replay(),full.export_replay())
        self.assertEqual(light.snapshot()['trace'],full.snapshot()['trace'])

    def test_invalid_observation_option_cannot_execute(self):
        c=SchedulerController();token=c.pause();before=c.checkpoint()
        with self.assertRaises(ValueError):c.step_once(token,{'jump':True},include_trace=0)
        self.assertEqual(c.checkpoint(),before)

    def test_failed_light_step_still_rolls_back(self):
        c=SchedulerController();token=c.pause();before=c.snapshot()['state']
        with patch('engine.runtime.camera.update',side_effect=RuntimeError('fixture fault')):
            with self.assertRaises(RuntimeError):c.step_frame_once(token,.02,{'jump':True},include_trace=False)
        after=c.snapshot()
        self.assertEqual(after['state']['body'],before['body'])
        self.assertEqual(after['state']['input_generation'],before['input_generation'])
        self.assertTrue(after['control']['paused'])
        self.assertEqual(len(after['incidents']),1)
