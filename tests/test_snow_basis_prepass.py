import math
import unittest
from engine.snow_basis_prepass import basis_prepass


class BasisPrepassTests(unittest.TestCase):
    def run_prepass(self,mode,primary):
        state=dict(config_valid_byte=1,immersion_selector_byte=0,mode_byte=mode,
                   frame_basis=[[0,1,0,0],[1,0,0,0],[0,0,1,0]],
                   incoming_axis0=[2,0,0,0],primary_immersion=primary,
                   alternate_immersion=.7,normal=[0,0,1,0],speed_argument=5,
                   direct_angle=0,curve_angle=0,
                   control_angle=dict(inhibit_byte=0,candidate_byte=0,preferred_byte=0,
                                      suppress_byte=0,retention_byte=0,prior_gate_byte=9,
                                      control_a=0,control_b=0,sign_gain=0,override=0,
                                      drive=0,base_angle=0,added_angle=0,candidate_gain=1))
        calls=[]
        def curve(x):calls.append(x);return 1.
        curves={k:curve for k in ('control_speed','control_immersion','finish_speed','finish_immersion')}
        return basis_prepass(state,curves,math.acos,math.sin,math.cos,lambda n:1/math.sqrt(n)),calls

    def test_nonzero_mode_selects_frame_but_only_one_runs_control_angle(self):
        r,calls=self.run_prepass(2,1)
        self.assertEqual(r['gate_byte'],9)
        self.assertFalse(r['gate_written'])
        self.assertEqual(calls,[5,.699999988079071])
        r,calls=self.run_prepass(1,1)
        self.assertTrue(r['gate_written'])
        self.assertEqual(len(calls),4)

    def test_primary_immersion_controls_replacement_not_selected_curve_argument(self):
        r,calls=self.run_prepass(0,0)
        self.assertTrue(r['replaced'])
        self.assertEqual(r['basis'],[[2,0,0,0],[0,0,1,0],[0,1,0,0]])
        self.assertGreater(calls[-1],0)
