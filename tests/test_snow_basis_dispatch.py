import math
import unittest
from engine.snow_basis_dispatch import dispatch_basis
from reference.central_impulse import f32


class BasisDispatchTests(unittest.TestCase):
    def run_state(self, **changes):
        state=dict(preferred_byte=1, preferred_gate_vector=[0,0,0,1],
                   inhibit_byte=0,rebuild_byte=0,clear_secondary_byte=5,
                   saved_basis=[[2,0,0,0],[0,3,0,0],[0,0,4,0]],
                   secondary_angle=1,explicit_triplet_byte=1,alignment_byte=1,
                   explicit_triplet=[[2,0,0,0],[0,3,0,0],[0,0,4,0]])
        state.update(changes)
        return dispatch_basis(state,math.sin,math.cos,lambda n:1/math.sqrt(n))

    def test_w_lane_can_select_preferred_and_skip_lower_operands(self):
        r=self.run_state(explicit_triplet=None)
        self.assertEqual(r['branch'],'preferred_reuse')
        self.assertFalse(r['cache_written'])
        self.assertEqual(r['clear_secondary_byte'],5)

    def test_exact_threshold_falls_through_and_triplet_beats_alignment(self):
        r=self.run_state(preferred_gate_vector=[f32(1e-5),0,0,0])
        self.assertEqual(r['branch'],'explicit_triplet')
        self.assertTrue(r['cache_written'])

    def test_inhibit_and_disabled_preference_fall_through(self):
        self.assertEqual(self.run_state(inhibit_byte=255)['branch'],'explicit_triplet')
        self.assertEqual(self.run_state(preferred_byte=0,preferred_gate_vector=None)['branch'],
                         'explicit_triplet')
