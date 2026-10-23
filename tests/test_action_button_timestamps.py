import struct
import unittest
from engine.action_button_timestamps import ButtonTimestamps,refresh_button_timestamps

class TimestampTests(unittest.TestCase):
    def state(self):return ButtonTimestamps(5,4,7,6,(1,)*256,(2,)*256,(3,)*10,(4,)*10)
    def refresh(self,keys,previous,packet=bytes(20),old=bytes(20)):
        return refresh_button_timestamps(self.state(),keys=keys,previous_keys=previous,packet=packet,previous_packet=old,now=20,secondary_now=30)
    def test_new_press_held_release(self):
        keys=bytes([1,128,0])+bytes(253);old=bytes([0,1,128])+bytes(253)
        r=self.refresh(keys,old)
        self.assertEqual(r.keys[:3],(20,1,1));self.assertEqual(r.secondary_keys[:3],(30,2,2))
        self.assertEqual((r.current,r.previous,r.secondary_current,r.secondary_previous),(20,5,30,7))
    def test_special_nonzero_and_sign_reversal(self):
        p=bytearray(20);p[12]=1;struct.pack_into('<i',p,8,1)
        r=self.refresh(bytes(256),bytes(256),bytes(p))
        self.assertEqual(r.special[0],20);self.assertEqual(r.special[8],20)
        old=bytearray(20);struct.pack_into('<i',old,8,-1)
        r=self.refresh(bytes(256),bytes(256),bytes(p),bytes(old))
        self.assertEqual(r.special[8:],(3,3))
