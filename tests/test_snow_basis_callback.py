import math
import unittest
from engine.snow_basis_callback import basis_callback


class BasisCallbackTests(unittest.TestCase):
    def test_disabled_needs_no_stage_inputs_and_preserves_output(self):
        def unused(*args):raise AssertionError('unused service')
        initial=[[2,0,0,0],[0,3,0,0],[0,0,4,0]]
        r=basis_callback(0,initial,None,None,None,unused,unused,unused,unused)
        self.assertFalse(r['success'])
        self.assertFalse(r['auxiliary_written'])
        self.assertEqual(r['basis'],initial)
        r['basis'][0][0]=3
        self.assertEqual(initial[0][0],2)

    def test_prepass_runs_before_preferred_cache_reuse(self):
        pre=dict(config_valid_byte=1,immersion_selector_byte=1,mode_byte=1,
                 frame_basis=[[0,1,0,0],[1,0,0,0],[0,0,1,0]],
                 primary_immersion=.5,alternate_immersion=.8,
                 normal=[0,0,1,0],speed_argument=4,direct_angle=0,curve_angle=0,
                 control_angle=dict(inhibit_byte=0,candidate_byte=0,
                     suppress_byte=0,retention_byte=0,prior_gate_byte=7,
                     control_a=0,control_b=0,sign_gain=0,override=0,drive=0,
                     base_angle=0,added_angle=0,candidate_gain=1))
        saved=[[2,0,0,0],[0,3,0,0],[0,0,4,0]]
        override=dict(preferred_byte=1,preferred_gate_vector=[1,0,0,0],
                      inhibit_byte=0,rebuild_byte=0,saved_basis=saved,
                      secondary_angle=1,clear_secondary_byte=2)
        calls=[]
        def curve(x):calls.append(x);return 1.
        r=basis_callback(1,saved,pre,override,
                         {'finish_speed':curve,'finish_immersion':curve},
                         math.acos,math.sin,math.cos,lambda n:1/math.sqrt(n))
        self.assertEqual(r['basis'],saved)
        self.assertFalse(r['cache_written'])
        self.assertEqual(r['gate_byte'],0)
        self.assertTrue(r['auxiliary_written'])
        self.assertEqual(calls,[4,.5])
        self.assertNotIn('preferred_byte',pre['control_angle'])
