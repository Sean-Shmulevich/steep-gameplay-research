import unittest
from reference.decay_table import build, sample_arguments, evaluate
from reference.central_impulse import f32


class DecayTableTests(unittest.TestCase):
    def test_sample_grid_and_constant_table(self):
        xs=sample_arguments()
        self.assertEqual((len(xs),xs[0],xs[-1]),(257,-10,0))
        table=build([.5]*257)
        for x in (-100,-10,-.1,0,100): self.assertEqual(evaluate(x,**table),.5)
    def test_padding_is_width_scaled_without_generic_curve_cap(self):
        table=build([1]*257)
        self.assertEqual(table['start'],f32(-10-f32(f32(10)*f32(.0001))))
        self.assertLess(table['start'],-10.0005)
    def test_linear_samples_keep_slope_and_clamp(self):
        table=build(sample_arguments())
        self.assertEqual(table['segments'][100],(1,0))
        self.assertEqual(evaluate(-20,**table),table['start'])
        upper=f32(f32(f32(256)/table['index_scale'])+table['start'])
        self.assertEqual(evaluate(10,**table),upper)
    def test_requires_complete_samples_and_valid_domain(self):
        with self.assertRaises(ValueError): build([0]*256)
        with self.assertRaises(ValueError): build([0]*257,low=0,high=0)
