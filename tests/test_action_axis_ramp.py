import unittest
from engine.action_axis_ramp import AxisRampState,transition_axis,ramp_axes,clock_scalar

class AxisRampTests(unittest.TestCase):
    def test_release_remembers_sign_and_reversal_clears_timer(self):
        state=transition_axis(0,AxisRampState(2,2,.5))
        self.assertEqual(state,AxisRampState(1,2,.5))
        self.assertEqual(transition_axis(-1,state),AxisRampState(0,0,0.))
    def test_press_release_and_bypass(self):
        kwargs=dict(duration=1,axis_mode=0,previous_clock=0,start_ticks=250,end_ticks=260,curve=lambda x:x)
        r=ramp_axes([1,0,3,4],[AxisRampState(1,0,0)],**kwargs)
        self.assertEqual(r['output'],[.25,0,3,4])
        self.assertEqual(r['clock'],clock_scalar(260))
        r=ramp_axes([0,0,3,4],[AxisRampState(2,2,.5)],**kwargs)
        self.assertEqual(r['output'][0],.25)
        r=ramp_axes([1,0,3,4],[AxisRampState(1,0,0)],active=False,**kwargs)
        self.assertEqual(r['output'],[1,0,3,4]);self.assertEqual(r['clock'],0)
    def test_skipped_axis_retains_state_and_does_not_call_curve(self):
        def fail(x):raise AssertionError('curve called')
        states=[AxisRampState(1,0,0)]
        r=ramp_axes([1,0,0,0],states,duration=1,axis_mode=2,previous_clock=0,start_ticks=100,end_ticks=100,curve=fail)
        self.assertEqual(r['states'],tuple(states));self.assertEqual(r['output'][0],1)
    def test_clock_extremes_and_missing_provider(self):
        self.assertEqual(clock_scalar(None),0.)
        self.assertEqual(clock_scalar(1000),1.)
        self.assertEqual(clock_scalar((1<<63)-1),clock_scalar(1<<63))
        self.assertGreater(clock_scalar((1<<64)-1),clock_scalar(1<<63))
    def test_backward_clock_and_timer_cap(self):
        r=ramp_axes([1,0,0,0],[AxisRampState(2,2,.5)],duration=1,axis_mode=0,
                    previous_clock=1,start_ticks=500,end_ticks=500,curve=lambda x:x)
        self.assertEqual(r['states'][0].timer,0)
        self.assertEqual(r['curve_inputs'],())
        r=ramp_axes([1,0,0,0],[AxisRampState(2,2,.5)],duration=1,axis_mode=0,
                    previous_clock=0,start_ticks=1000,end_ticks=1000,curve=lambda x:x)
        self.assertEqual(r['states'][0].timer,1)
