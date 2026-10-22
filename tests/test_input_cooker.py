import unittest
from reference.input_cooker import cook
from reference.central_impulse import f32


class InputCookerTests(unittest.TestCase):
    coeff=dict(baseDampFactorToZero=10,proportionalDampFactorToZero=20,
               baseDampFactorToOne=2,proportionalDampFactorToOne=1)
    def test_starting_zero_and_sign_cross_use_zero_branch(self):
        for current,target in ((0,1),(-.5,.5),(.5,-.5),(.5,.5)):
            result=cook(current,target,.01,self.coeff,decay_lookup=lambda x:1)
            self.assertEqual(result['direction'],'ToZero')
    def test_growing_same_sign_uses_one_branch(self):
        result=cook(.25,1,.125,self.coeff,decay_lookup=lambda x:.5)
        self.assertEqual(result['direction'],'ToOne')
        self.assertEqual(result['lookup_argument'],-.125)
        self.assertEqual(result['value'],.875)
    def test_overshoot_clamped_both_directions(self):
        for current,target in ((0,1),(1,0)):
            self.assertEqual(cook(current,target,1,self.coeff,decay_lookup=lambda x:0)['value'],target)
    def test_exact_epsilon_not_snapped(self):
        coeff={k:0 for k in self.coeff}
        result=cook(0,.125,0,coeff,decay_lookup=lambda x:1,epsilon=.125)
        self.assertEqual(result['value'],0)
        self.assertEqual(cook(0,.125,0,coeff,decay_lookup=lambda x:1,epsilon=.126)['value'],.125)
    def test_lookup_is_required_and_nonfinite_refused(self):
        with self.assertRaises(TypeError): cook(0,1,.01,self.coeff)
        with self.assertRaises(ValueError): cook(0,1,.01,self.coeff,decay_lookup=lambda x:float('nan'))
