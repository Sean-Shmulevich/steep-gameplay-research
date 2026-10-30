import struct
import unittest
from engine.pose_endpoint_rings import attach_pose_endpoint_rings,detach_pose_endpoint_rings
from engine.pose_command_registry import register_pose_constraint,unregister_pose_constraint


class RingTests(unittest.TestCase):
    def fixture(self):
        records={}
        for token,a,b in ((10,1,2),(20,3,1),(30,1,3)):
            record=bytearray(0x60);struct.pack_into('<2Q',record,8,a,b);records[token]=record
        return records,{i:bytearray(0xa0) for i in (1,2,3)}

    def test_mixed_endpoint_ports_and_head_removal(self):
        r,b=self.fixture()
        for t in r:attach_pose_endpoint_rings(t,2,records=r,bodies=b)
        self.assertEqual(struct.unpack_from('<Q',b[1],0x90)[0],10)
        self.assertEqual(struct.unpack_from('<2Q',r[10],0x20),(30,20))
        self.assertEqual(struct.unpack_from('<2Q',r[20],0x30),(10,30))
        detach_pose_endpoint_rings(10,2,records=r,bodies=b)
        self.assertEqual(struct.unpack_from('<Q',b[1],0x90)[0],20)
        self.assertEqual(struct.unpack_from('<Q',b[2],0x90)[0],0)
        self.assertEqual(r[10][0x20:0x40],bytes(32))
        for t in (30,20):detach_pose_endpoint_rings(t,2,records=r,bodies=b)
        self.assertTrue(all(struct.unpack_from('<Q',v,0x90)[0]==0 for v in b.values()))

    def test_selectors_do_not_overwrite_other_heads(self):
        for selector,offset in ((0,0x88),(1,0x80),(2,0x90)):
            r,b=self.fixture()
            for v in b.values():
                for off in (0x80,0x88,0x90):struct.pack_into('<Q',v,off,0 if off==offset else 99)
            attach_pose_endpoint_rings(10,selector,records=r,bodies=b)
            detach_pose_endpoint_rings(10,selector,records=r,bodies=b)
            for off in (0x80,0x88,0x90):
                self.assertEqual(struct.unpack_from('<Q',b[1],off)[0],0 if off==offset else 99)

    def test_individual_registration_uses_real_ring_attachment(self):
        r,b=self.fixture();p=bytearray(0x90);arrays={100:[0]*8,200:[0]*8}
        struct.pack_into('<QII',p,0x60,100,0,8);struct.pack_into('<QII',p,0x70,200,0,8)
        register_pose_constraint(p,10,arrays=arrays,grow=lambda *x:self.fail('growth'),
            notify=lambda t,s:attach_pose_endpoint_rings(t,s,records=r,bodies=b),get_kind=lambda t:4)
        self.assertEqual(arrays[100][0],10);self.assertEqual(arrays[200][0],10)
        self.assertEqual(struct.unpack_from('<Q',b[1],0x90)[0],10)
        self.assertEqual(struct.unpack_from('<Q',b[2],0x90)[0],10)
        unregister_pose_constraint(p,10,arrays=arrays,get_kind=lambda t:4,
            detach=lambda t,s:detach_pose_endpoint_rings(t,s,records=r,bodies=b))
        self.assertEqual(struct.unpack_from('<I',p,0x68)[0],0)
        self.assertEqual(struct.unpack_from('<I',p,0x78)[0],0)
        self.assertEqual(r[10][0x20:0x40],bytes(32))
        self.assertEqual(struct.unpack_from('<Q',b[1],0x90)[0],0)
        self.assertEqual(struct.unpack_from('<Q',b[2],0x90)[0],0)


if __name__=='__main__':unittest.main()
