import struct
import unittest
from engine.pose_command_registry import (register_pose_constraint,
    process_pose_body_constraints,unregister_pose_constraint_container)
from engine.pose_endpoint_rings import attach_pose_endpoint_rings


def put(raw,offset,fmt,*values):struct.pack_into('<'+fmt,raw,offset,*values)
def get(raw,offset,fmt='I'):return struct.unpack_from('<'+fmt,raw,offset)[0]


class BodyRemovalTests(unittest.TestCase):
    def fixture(self):
        self.p=bytearray(0xe0);self.out=bytearray(16);self.arrays={100:[0]*8,200:[0]*8,300:[]}
        put(self.p,0x60,'QII',100,0,8);put(self.p,0x70,'QII',200,0,8);put(self.out,0,'QII',300,0,0)
        self.bodies={i:bytearray(0xa0) for i in (1,2,3)};self.meta={i:bytearray(0x60) for i in (11,12,13)}
        for i,owner in ((1,10),(2,20),(3,10)):
            put(self.bodies[i],0x30,'Q',i+10);put(self.meta[i+10],0x20,'Q',owner)
        self.records={};self.destroyed=[]
        self.kw=dict(constraints=self.records,bodies=self.bodies,metadata=self.meta,arrays=self.arrays,
            get_kind=lambda t:4,destroy=lambda t,f:self.destroyed.append((t,f)),grow_output=self.grow)
        for t,a,b in ((30,1,3),(40,2,1),(50,1,2)):
            self.records[t]=bytearray(0x60);put(self.records[t],8,'QQ',a,b)
            register_pose_constraint(self.p,t,arrays=self.arrays,grow=lambda *a:self.fail('capacity'),get_kind=lambda t:4,
                notify=lambda t,s:attach_pose_endpoint_rings(t,s,records=self.records,bodies=self.bodies))

    def grow(self,out,capacity):
        old=get(out,0,'Q');count=get(out,8);self.arrays[400]=self.arrays[old][:count]+[0]*(capacity-count)
        put(out,0,'QII',400,count,capacity)

    def process(self,out):process_pose_body_constraints(self.p,1,out,**self.kw)

    def test_restart_preserves_internal_edge_and_queues_cross_owner_edges(self):
        self.fixture();self.process(self.out)
        self.assertEqual(set(self.arrays[400][:get(self.out,8)]),{40,50});self.assertEqual(self.destroyed,[])
        self.assertEqual(get(self.p,0x68),1);self.assertEqual(self.arrays[100][0],30)
        self.assertEqual(get(self.bodies[1],0x90,'Q'),30)
        self.assertEqual(self.records[40][0x20:0x40],bytes(32))
        self.process(self.out);self.assertEqual(get(self.out,8),2)

    def test_absent_output_and_metadata_gates_destroy_after_detach(self):
        for output in (False,True):
            self.fixture();self.meta[12][0x52]=1
            def destroy(t,f):
                self.assertEqual(self.records[t][0x20:0x40],bytes(32));self.destroyed.append((t,f))
            self.kw['destroy']=destroy;self.process(self.out if output else None)
            self.assertEqual(set(self.destroyed),{(40,1),(50,1)});self.assertEqual(get(self.out,8),0)

    def test_zero_owner_asymmetry(self):
        self.fixture();put(self.meta[12],0x20,'Q',0);self.process(self.out)
        self.assertEqual(self.arrays[400][:get(self.out,8)],[40])
        self.assertEqual(get(self.p,0x68),2)

    def test_container_uses_real_body_processing(self):
        self.fixture();c=bytearray(0x68);put(c,0x20,'Q',99);put(c,0x38,'QI',500,1)
        self.arrays[500]=[1];self.arrays[600]=[77];put(self.p,0x50,'QII',600,1,1)
        unregister_pose_constraint_container(self.p,77,self.out,provider_token=999,containers={77:c},
            constraints=self.records,bodies=self.bodies,metadata=self.meta,arrays=self.arrays,get_kind=lambda t:4,
            remove_tree_body=lambda *a:self.fail('not tree flagged'),
            process_body=lambda p,b,o:process_pose_body_constraints(self.p,b,o,**self.kw),grow_output=self.grow)
        self.assertEqual(get(self.p,0x58),0);self.assertEqual(get(c,0x30),0xffffffff)
        self.assertEqual(get(self.p,0x68),1);self.assertEqual(get(self.out,8),2)


if __name__=='__main__':unittest.main()
