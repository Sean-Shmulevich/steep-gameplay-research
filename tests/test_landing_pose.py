import math
import unittest
from reference.landing_pose import *

class PoseTests(unittest.TestCase):
    def test_ordinary_weight(self):
        self.assertEqual(alignment_weight(.5,1.,.1), .5)
        self.assertEqual(alignment_weight(.5,.1,.1), 0.)
    def test_delayed_override(self):
        self.assertAlmostEqual(alignment_weight(1.,1.,2.,.2), DELAY_SCALE)
        self.assertEqual(alignment_weight(.1,1.,.1,.2), 0.)
        self.assertEqual(alignment_weight(2.,1.,.1,.2), 1.)
    def test_invalid_domain(self):
        with self.assertRaises(ValueError): alignment_weight(.5,1.,.1,1.)
    def test_half_angle(self):
        up=align_basis(IDENTITY,(0.,0.,1.),(1.,0.,0.),.5)[2]
        self.assertAlmostEqual(up[0], math.sqrt(.5))
        self.assertAlmostEqual(up[2], math.sqrt(.5))
    def test_degenerate_and_raw_threshold(self):
        self.assertEqual(align_basis(IDENTITY,(0.,0.,1.),(0.,0.,-1.),1.), IDENTITY)
        self.assertEqual(align_basis(IDENTITY,(0.,0.,.001),(.001,0.,0.),1.), IDENTITY)
    def test_preserve_orthonormality(self):
        b=tilt_basis(align_basis(IDENTITY,(0.,0.,1.),(1.,2.,3.),.7),(4.,5.,6.),-.8)
        for i in range(3):
            for j in range(3): self.assertAlmostEqual(dot(b[i],b[j]),float(i==j))
    def test_motion_plane_and_sign(self):
        b=tilt_basis(IDENTITY,(10.,0.,100.),-.2)
        self.assertLess(b[2][0],0.)
        self.assertEqual(b,tilt_basis(IDENTITY,(10.,0.,0.),-.2))
        self.assertEqual(tilt_basis(IDENTITY,(0.,0.,100.),-.2),IDENTITY)
    def test_response_onset(self):
        self.assertEqual(delayed_response(.1,.2,.3,.1),0.)
        self.assertEqual(delayed_response(.2,.2,.3,.1),0.)
        self.assertLess(delayed_response(.3,.2,.3,.1),0.)
    def test_translation(self):
        self.assertEqual(shifted_translation((1.,2.,3.),(4.,5.,6.),(2.,3.,4.)),(-1.,0.,1.,1.))

if __name__ == '__main__': unittest.main()
