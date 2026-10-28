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


class ContactPairHandoffTest(unittest.TestCase):
    def test_generation_precedes_grouping_or_clear(self):
        from engine.pose_contact_dispatch import dispatch_contact_pair
        for count in (0,1,500):
            for width in (16,32):
                events=[];output=bytearray(24000);descriptor=object()
                cache=object();recycled=object()
                def generate(d, records, capacity):
                    self.assertIs(d,descriptor);self.assertIs(records,output)
                    self.assertEqual(capacity,500)
                    records[0]=91;events.append('generate');return count
                def groups(c,records,n,first,second,r,w):
                    self.assertIs(c,cache);self.assertIs(r,recycled)
                    self.assertIs(records,output);self.assertEqual(records[0],91)
                    self.assertEqual((n,first,second,w),(count,1,0,width))
                    events.append('groups')
                def clear(c,first,second,r):
                    self.assertIs(c,cache);self.assertIs(r,recycled)
                    self.assertEqual((first,second),(1,0));events.append('clear')
                handlers=[None]*64;handlers[59]=generate
                result=dispatch_contact_pair(handlers,[{'kind':0},{'kind':0x8007}],
                    [{'kind':3}],1,0,descriptor,output,cache=cache,recycled=recycled,
                    key_width=width,process_groups=groups,clear_pair=clear)
                self.assertEqual(result,count)
                self.assertEqual(events,['generate','groups' if count else 'clear'])
