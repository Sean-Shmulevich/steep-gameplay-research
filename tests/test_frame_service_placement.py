import unittest
from engine.frame_service_placement import frame_service_placement

class FrameServicePlacementTests(unittest.TestCase):
    def test_stable_predicate_selects_one_site(self):
        for first,last in [(0,0),(1,1),(1,255),(255,2)]:
            r=frame_service_placement(first,last)
            self.assertEqual(r['call_count'],1)
            self.assertTrue(r['predicate_stable'])

    def test_changed_predicate_can_duplicate_or_skip(self):
        self.assertEqual(frame_service_placement(0,1)['calls'],['site_a','begin_graphic_frame'])
        self.assertEqual(frame_service_placement(1,0)['calls'],[])

    def test_invalid_samples(self):
        for value in (-1,256,True):
            with self.assertRaises(ValueError):frame_service_placement(value,0)
