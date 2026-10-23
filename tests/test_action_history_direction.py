import struct
import unittest
from engine.action_history_direction import history_direction_matches


class HistoryDirectionTests(unittest.TestCase):
    def state(self, direction, magnitude=1):
        state=bytearray(0x3c0)
        struct.pack_into('<4f',state,0x1a0,*direction)
        struct.pack_into('<f',state,0x2e0,magnitude)
        return bytes(state)

    def test_axes_and_unknown_sector(self):
        for vector, sector in (((0,1,0,0),0),((0,-1,0,0),1),((1,0,0,0),3),((-1,0,0,0),2)):
            state=self.state(vector)
            for request in range(5):
                self.assertEqual(history_direction_matches(state,(0,1,0,0),
                    magnitude_threshold=.5,sector=request)['matches'],request==sector)

    def test_threshold_is_strict_and_precedes_direction_read(self):
        state=self.state((0,0,0,0),.5)
        self.assertFalse(history_direction_matches(state,None,magnitude_threshold=.5,sector=0)['matches'])
        with self.assertRaises(ValueError):
            history_direction_matches(state,(0,1,0,0),magnitude_threshold=.4,sector=0)

    def test_curve_history_is_not_read(self):
        state=bytearray(self.state((1,0,0,0)))
        struct.pack_into('<4f',state,0x240,0,1,0,0)
        self.assertTrue(history_direction_matches(bytes(state),(0,1,0,0),
            magnitude_threshold=0,sector=3)['matches'])
