import unittest
from engine.pose_contact_dispatch import select_contact_handler


class ContactDispatchTest(unittest.TestCase):
    def test_order_and_high_bit(self):
        handlers=[None]*64
        handlers[7*8+3]='terrain_box'
        handlers[3*8+7]='box_terrain'
        for high_first in (0,0x8000):
            for high_second in (0,0x8000):
                self.assertEqual(select_contact_handler(handlers,7|high_first,3|high_second),'terrain_box')
                self.assertEqual(select_contact_handler(handlers,3|high_first,7|high_second),'box_terrain')
        self.assertIsNone(select_contact_handler(handlers,6,7))

    def test_authored_guards(self):
        for kinds in ((8,0),(0,0xffff),(-1,3),(True,3)):
            with self.assertRaises(ValueError):
                select_contact_handler([None]*64,*kinds)
        with self.assertRaises(ValueError):
            select_contact_handler([None]*63,0,0)
