import math
import unittest
from reference.response_delay import response_delay, delayed_response


class DelayTests(unittest.TestCase):
    def test_logarithmic_example(self):self.assertAlmostEqual(response_delay(2,2,4),math.log(2)/2)
    def test_negative_sum_and_negative_result(self):
        self.assertEqual(response_delay(2,-3,4),0)
        self.assertEqual(response_delay(2,-1,4),0)
    def test_actor_scaling(self):self.assertAlmostEqual(response_delay(2,2,8)*2,response_delay(2,2,4))
    def test_invalid_domains(self):
        for args in [(2,-2,4),(0,2,4),(2,2,0),(-1,2,4)]:
            with self.assertRaises(ValueError):response_delay(*args)
    def test_onset_continuity_and_derivative(self):
        d=response_delay(2,2,4)
        self.assertEqual(delayed_response(d-.1,d,.01,.01),0)
        self.assertEqual(delayed_response(d,d,.01,.01),0)
        h=1e-6
        self.assertLess(abs(delayed_response(d+h,d,.01,.01)/h),1e-6)
    def test_response_slope(self):
        d=.3;t=.4;h=1e-6;g=.01;tau=.1
        derivative=(delayed_response(t+h,d,g,tau)-delayed_response(t-h,d,g,tau))/(2*h)
        self.assertAlmostEqual(derivative,-g*(1-math.exp(-(t-d)/tau)),places=10)


if __name__=='__main__':unittest.main()
