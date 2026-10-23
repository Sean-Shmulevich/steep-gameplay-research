import struct
import unittest
from engine.action_history_action import evaluate_history_action


class HistoryActionTests(unittest.TestCase):
    def run_action(self, gates, previous=False):
        action=bytearray([0xa5]*0xe0)
        action[0xb8]=previous
        struct.pack_into('<2Q',action,0xc0,100,190)
        history=bytearray(0x3c0)
        struct.pack_into('<4f',history,0x1a0,0,1,0,0)
        struct.pack_into('<f',history,0x2e0,.75)
        it=iter(gates)
        result=evaluate_history_action(bytes(action),bytes(history),(0,1,0,0),
            direction_kind=0,magnitude_threshold=.5,mode=0,hold_delay=0,
            repeat_delay=0,ownership_blocked=lambda:next(it),
            read_clock=lambda:self.fail('edge must not read clock'))
        return bytes(action),result

    def test_second_gate_suppresses_magnitude_not_event(self):
        initial,result=self.run_action((False,True))
        self.assertTrue(result['timing']['active'])
        self.assertEqual(result['magnitude'],0)
        changed={0x30,0xb8,*range(0x60,0x64),*range(0xc0,0xd0)}
        self.assertTrue(all(a==b for i,(a,b) in enumerate(zip(initial,result['snapshot'])) if i not in changed))

    def test_first_gate_suppresses_detection_not_later_magnitude(self):
        _,result=self.run_action((True,False))
        self.assertIsNone(result['detection'])
        self.assertFalse(result['timing']['active'])
        self.assertEqual(result['magnitude'],.75)
