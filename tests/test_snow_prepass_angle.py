import unittest
from engine.snow_prepass_angle import control_prepass_angle


class PrepassAngleTests(unittest.TestCase):
    def run_angle(self, **changes):
        inputs=dict(mode_byte=1,inhibit_byte=0,candidate_byte=1,preferred_byte=0,
                    suppress_byte=0,retention_byte=0,prior_gate_byte=8,
                    control_a=1,control_b=-1,sign_gain=1,override=0,drive=2,
                    base_angle=10,added_angle=3,candidate_gain=2,
                    speed_argument=4,immersion_argument=5,
                    speed_curve=lambda x:.5,immersion_curve=lambda x:.25)
        inputs.update(changes)
        return control_prepass_angle(**inputs)

    def test_candidate_excludes_base_and_uses_gain(self):
        self.assertEqual(self.run_angle()['angle'],-2.25)
        self.assertEqual(self.run_angle()['gate_byte'],1)
        self.assertEqual(self.run_angle(control_a=.5)['angle'],-2.375)
        self.assertEqual(self.run_angle(sign_gain=-1)['gate_byte'],0)

    def test_retention_overrides_candidate_angle_but_not_gate(self):
        r=self.run_angle(retention_byte=255)
        self.assertEqual(r['angle'],-1.625)
        self.assertEqual(r['gate_byte'],1)

    def test_skipped_modes_preserve_gate_and_preferred_clears_it(self):
        def unused(x):raise AssertionError('curve must not run')
        self.assertEqual(self.run_angle(mode_byte=2,speed_curve=unused),
                         {'angle':None,'gate_byte':8,'gate_written':False})
        self.assertEqual(self.run_angle(preferred_byte=128,speed_curve=unused),
                         {'angle':None,'gate_byte':0,'gate_written':True})
