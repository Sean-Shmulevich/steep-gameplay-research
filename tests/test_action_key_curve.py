import unittest
from engine.action_key_curve import CurveKey,evaluate_key_curve

class KeyCurveTests(unittest.TestCase):
    def key(self,x,y,mode=1):return CurveKey(x,y,(x,y),(x,y),mode)
    def test_empty_endpoints_and_duplicate_selection(self):
        self.assertEqual(evaluate_key_curve([],0,output_bounds=(2,3)),0)
        keys=[self.key(0,1),self.key(.5,2),self.key(.5,3),self.key(1,4)]
        self.assertEqual(evaluate_key_curve(keys,.5),3)
        self.assertEqual(evaluate_key_curve(keys,-1),1)
        self.assertEqual(evaluate_key_curve(keys,2),4)
    def test_linear_hold_and_clamps(self):
        keys=[self.key(0,0),self.key(1,2)]
        self.assertEqual(evaluate_key_curve(keys,.25),.5)
        self.assertEqual(evaluate_key_curve(keys,-1,input_bounds=(.5,1)),1)
        self.assertEqual(evaluate_key_curve(keys,.75,output_bounds=(0,1)),1)
        self.assertEqual(evaluate_key_curve([self.key(0,3,99),self.key(1,4)],.5),3)
    def test_cubic_requires_solver_and_uses_last_root(self):
        keys=[CurveKey(0,0,(0,0),(1/3,0),2),CurveKey(1,1,(2/3,1),(1,1),0)]
        with self.assertRaises(ValueError):evaluate_key_curve(keys,.5)
        self.assertEqual(evaluate_key_curve(keys,.5,solve_roots=lambda *a:(.1,.5)),.5)
        self.assertEqual(evaluate_key_curve(keys,.5,solve_roots=lambda *a:()),0)
        self.assertEqual(evaluate_key_curve(keys,.5,solve_roots=lambda *a:(2,)),1)
