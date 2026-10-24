import math
import unittest
from engine.snow_slope_angle import build_slope_angle_table, evaluate_slope_angle


class SlopeAngleTests(unittest.TestCase):
    def test_batch_contract_and_padded_lookup(self):
        batches=[];endpoint=[]
        def vector(xs):batches.append(xs);return [math.acos(x) for x in xs]
        def scalar(x):endpoint.append(x);return math.acos(x)
        table=build_slope_angle_table(vector,scalar)
        self.assertEqual(len(batches),64)
        self.assertEqual(batches[0],(-1.,-.9921875,-.984375,-.9765625))
        self.assertEqual(endpoint,[1.])
        self.assertLess(table['start'],-1.)
        self.assertEqual(evaluate_slope_angle(-2,table),evaluate_slope_angle(table['start'],table))
        self.assertLess(evaluate_slope_angle(2,table),0.)

    def test_invalid_vector_width_rejected(self):
        with self.assertRaises(ValueError):build_slope_angle_table(lambda xs:[0],math.acos)
