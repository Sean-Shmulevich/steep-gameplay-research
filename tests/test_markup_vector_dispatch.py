import unittest
from engine.markup_vector_dispatch import select_vector_route, dispatch_vector


class VectorDispatchTests(unittest.TestCase):
    def test_preserve_differs_from_zero(self):
        def no_call(*args):self.fail('unexpected invocation')
        v=[1.,2.,3.,4.]
        self.assertEqual(dispatch_vector(1,None,None,v,no_call),1)
        self.assertEqual(v,[1.,2.,3.,4.])
        self.assertEqual(dispatch_vector(0,2,None,v,no_call),0)
        self.assertEqual(v,[0.]*4)

    def test_routes_and_callback_output(self):
        for outer,inner,route,depth in [(1,None,'projection_outer_one',1),(3,None,'direction_outer_three',1),(0,5,'projection_inner_five',2)]:
            v=[0.]*4;calls=[]
            def invoke(label,d,output):calls.append((label,d));output[:]=[1.,2.,3.,4.];return 999
            self.assertEqual(dispatch_vector(0,outer,inner,v,invoke),0)
            self.assertEqual(calls,[(route,depth)]);self.assertEqual(v,[1.,2.,3.,4.])
        with self.assertRaises(ValueError):select_vector_route(0,0,None)
