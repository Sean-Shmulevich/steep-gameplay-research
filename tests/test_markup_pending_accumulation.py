import unittest
from engine.markup_pending import queue_world_scaled_pending
from reference.central_impulse import f32


class ScaledPendingTests(unittest.TestCase):
    def test_all_lanes_accumulate_and_input_is_unchanged(self):
        pending=[1.,2.,3.,4.];v=[2.,4.,6.,8.]
        self.assertEqual(queue_world_scaled_pending(pending,v,1/60),(2.,4.,6.,8.))
        self.assertEqual(pending,[1.,2.,3.,4.]);self.assertEqual(v,[2.,4.,6.,8.])

    def test_interval_zero_and_negative_not_silently_clamped(self):
        self.assertEqual(queue_world_scaled_pending([1.]*4,[2.]*4,0),(1.,)*4)
        self.assertEqual(queue_world_scaled_pending([1.]*4,[2.]*4,-1/60),(0.,)*4)

    def test_multiply_order(self):
        interval=f32(.0137);v=f32(3.14159)
        expected=f32(f32(f32(interval*30.)*v)+f32(.12345))
        self.assertEqual(queue_world_scaled_pending([.12345]*4,[v]*4,interval),(expected,)*4)
