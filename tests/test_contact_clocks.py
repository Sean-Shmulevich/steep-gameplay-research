import unittest
from reference.contact_clocks import advance
from reference.central_impulse import f32


class ContactClocksTests(unittest.TestCase):
    def test_threshold_clears_immersion_before_normal_gate(self):
        for immersion in (0,.00001,.001):
            state=advance(immersion,.1,.3,.01)
            self.assertEqual(state['immersion'],0)
            self.assertEqual(state['contact_time'],0)
            self.assertGreater(state['air_time'],.1)

    def test_contact_time_accumulates_then_resets_on_air(self):
        state={'immersion':.5,'air_time':1.,'contact_time':0.}
        for _ in range(21):state=advance(.5,state['air_time'],state['contact_time'],.01)
        self.assertEqual(state['air_time'],0)
        self.assertGreater(state['contact_time'],f32(.2))
        state=advance(0,state['air_time'],state['contact_time'],.01)
        self.assertEqual(state['contact_time'],0)
        self.assertEqual(state['air_time'],f32(.01))
