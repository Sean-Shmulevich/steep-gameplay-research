import struct
import unittest
from engine.pose_command_registry import unregister_pose_constraint_container


def put(raw,offset,fmt,*values):struct.pack_into('<'+fmt,raw,offset,*values)
def get(raw,offset,fmt='I'):return struct.unpack_from('<'+fmt,raw,offset)[0]


class ContainerRemovalTests(unittest.TestCase):
    def fixture(self):
        self.p=bytearray(0xe0);self.c=bytearray(0x68);self.moved=bytearray(0x68)
        self.out=bytearray(16);self.events=[]
        self.arrays={100:[10,20],200:[30,40],300:[1,2],400:[30,40],500:[]}
        put(self.p,0x50,'QII',100,2,2);put(self.p,0x80,'QII',200,2,2)
        put(self.c,0x20,'QQI',99,88,0);put(self.c,0x38,'QI',300,2);put(self.c,0x58,'QI',400,2)
        put(self.out,0,'QII',500,0,0)
        self.bodies={i:bytearray(0x40) for i in (1,2)}
        self.meta={i:bytearray(0x60) for i in (11,12)}
        for i in (1,2):put(self.bodies[i],0x30,'Q',i+10)
        self.records={i:bytearray(0x20) for i in (30,40)}
        for r in self.records.values():put(r,8,'QQ',1,2)
        self.kw=dict(provider_token=1000,containers={10:self.c,20:self.moved},constraints=self.records,
            bodies=self.bodies,metadata=self.meta,arrays=self.arrays,get_kind=lambda t:4,
            remove_tree_body=lambda t,b:self.events.append(('tree',t,b)),
            process_body=lambda t,b,o:self.events.append(('body',t,b)),grow_output=self.grow)

    def grow(self,output,capacity):
        self.events.append(('grow',capacity));self.arrays[600]=[0]*capacity;put(output,0,'Q',600)

    def run_remove(self):unregister_pose_constraint_container(self.p,10,self.out,**self.kw)

    def test_service_order_growth_and_moved_backlinks(self):
        self.fixture();self.meta[11][0x52]=8;self.run_remove()
        self.assertEqual(self.events,[('tree',1208,1),('body',1000,1),('body',1000,2),('grow',8)])
        self.assertEqual(self.arrays[600][:2],[30,40]);self.assertEqual(get(self.p,0x88),0)
        self.assertEqual(self.arrays[100],[20,20]);self.assertEqual(get(self.p,0x58),1)
        self.assertEqual(get(self.c,0x30),0xffffffff);self.assertEqual(get(self.c,0x20,'Q'),0)
        self.assertEqual(get(self.moved,0x20,'Q'),99);self.assertEqual(get(self.moved,0x28,'Q'),1008)

    def test_counts_captured_at_different_times_and_endpoint_capture(self):
        self.fixture();seen=[]
        def body(p,b,o):
            seen.append(b);put(self.c,0x40,'I',0);self.arrays[301]=[2,1];put(self.c,0x38,'Q',301)
            put(self.c,0x60,'I',1);put(self.c,0x30,'I',1)
        def kind(t):
            put(self.records[t],8,'QQ',0,0);put(self.c,0x60,'I',0)
            return 4
        self.kw.update(process_body=body,get_kind=kind);self.run_remove()
        self.assertEqual(seen,[1,1]);self.assertEqual(self.arrays[600][0],30)
        self.assertEqual(get(self.out,8),1);self.assertEqual(self.arrays[100],[20,20])

    def test_metadata_gate_still_removes_command_and_missing_member_guard(self):
        self.fixture();self.meta[12][0x52]=1;self.run_remove()
        self.assertEqual(get(self.out,8),0);self.assertEqual(get(self.p,0x88),0)
        self.fixture();self.arrays[200]=[77,88]
        with self.assertRaises(ValueError):self.run_remove()
        self.assertEqual(get(self.p,0x58),2)


if __name__=='__main__':unittest.main()
