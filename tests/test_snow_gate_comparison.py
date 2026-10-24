import unittest
from engine.snow_gate_comparison import compare_gate_transition, bits


def sample(**changes):
    v=dict(immersion=0, alternate=0, activity=0, timer=0, elapsed=.125,
           total_volume=1, refill_divisor=2, duration=1, lower_one=.1, lower_other=.33)
    v.update(changes)
    return {k+'_bits':bits(x) for k,x in v.items()}


class GateComparisonTests(unittest.TestCase):
    def test_refill_then_contact_return_attenuation(self):
        a=sample(activity=.25)
        b=sample(activity=.375,timer=.1875)
        refill=compare_gate_transition(a,b)
        self.assertTrue(refill['duration_matches'] and refill['timer_matches'])
        self.assertEqual(refill['timer_action'],'refill')
        c=sample(immersion=1,activity=0,alternate=.125,timer=.0625)
        contact=compare_gate_transition(b,c)
        self.assertTrue(contact['duration_matches'] and contact['timer_matches'])
        self.assertEqual(contact['timer_action'],'attenuate')

    def test_negative_remainder_and_mismatch_are_visible(self):
        a=sample(immersion=1,alternate=.25,timer=-.25)
        b=sample(immersion=1,alternate=.375,timer=-.375)
        result=compare_gate_transition(a,b)
        self.assertTrue(result['timer_matches'])
        self.assertEqual(result['timer_action'],'expired')
        b['timer_bits']=bits(0)
        self.assertFalse(compare_gate_transition(a,b)['timer_matches'])

    def test_threshold_equality_and_untestable_observations(self):
        a=sample();b=sample(immersion=.001,activity=.125,timer=.0625)
        self.assertTrue(compare_gate_transition(a,b)['duration_matches'])
        b['duration_bits']=bits(2)
        self.assertEqual(compare_gate_transition(a,b)['status'],'configuration_changed')
        b['timer_bits']=0x7fc12345
        self.assertEqual(compare_gate_transition(a,b)['status'],'nonfinite')
        b['timer_bits']=True
        with self.assertRaises(ValueError):compare_gate_transition(a,b)
