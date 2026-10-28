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


class TerrainCacheIntegrationTest(unittest.TestCase):
    def test_actual_terrain_contact_then_separation_clears_pair(self):
        import struct
        from engine.pose_contact_dispatch import process_dispatched_contact_pair
        from engine.pose_grid_box_contact import emit_grid_box_contacts
        grid=bytearray(0xc0)
        struct.pack_into('<I',grid,0x40,2);struct.pack_into('<2H',grid,0x68,3,3)
        struct.pack_into('<2f',grid,0x70,1,1);struct.pack_into('<3f',grid,0x7c,0,0,-1)
        struct.pack_into('<3f',grid,0x88,2,2,1);struct.pack_into('<2H',grid,0x9c,2,2)
        terrain=[[1,0,0],[0,1,0],[0,0,1],[0,0,0]]
        box=[*terrain[:3],[.75,.75,-.1]]
        output=bytearray(24000);cache={'count':0,'slots':[bytes(16)]*8}
        recycle={'count':1,'capacity':8,'slots':[10]+[0]*7};payloads={10:bytearray(288)}
        def generate(descriptor,buffer,capacity):
            return emit_grid_box_contacts(buffer,capacity,grid,[0]*9,terrain,box,[.25]*3,
                {'default20':'p','mapb0':None,'tablea0':[]},{'default20':'p'},
                profiles={'p':{'mask48':1,'mask50':1}},preliminary=True)
        handlers=[None]*64;handlers[59]=generate
        def append(c,a,b,d,p):
            c['slots'][c['count']]=struct.pack('<HHIQ',a,b,d,p);c['count']+=1
        def supply(n):raise AssertionError('Unexpected refill')
        def run():
            return process_dispatched_contact_pair(handlers,[{'kind':7}],[{'kind':3}],
                0,0,None,output,cache=cache,recycled=recycle,key_width=32,owner=99,
                payloads=payloads,first_frame={'basis':terrain[:3],'translation':terrain[3]},
                second_frame={'basis':box[:3],'translation':box[3]},first_flags=0x14,
                second_flags=0x14,supply_batch=supply,append_entry=append)
        self.assertEqual(run()['generated_count'],1)
        self.assertEqual(cache['count'],1);self.assertEqual(recycle['count'],0)
        box[3]=[.75,.75,10]
        result=run()
        self.assertEqual(result,{'generated_count':0,'cleared_payloads':1})
        self.assertEqual(cache['count'],0);self.assertEqual(recycle['slots'][0],10)
        self.assertEqual(struct.unpack_from('<I',payloads[10],0x110)[0],0)
