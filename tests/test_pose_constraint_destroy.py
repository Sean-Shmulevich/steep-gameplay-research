import struct
import unittest
from engine.pose_constraint_destroy import destroy_pose_constraint
from engine.pose_command_registry import register_pose_constraint,process_pose_body_constraints
from engine.pose_endpoint_rings import attach_pose_endpoint_rings


class ConstraintDestroyTests(unittest.TestCase):
    def fixture(self):
        self.r=bytearray(0x200);self.records={7:self.r};self.bodies={1:bytearray(0xa0),2:bytearray(0xa0)}
        struct.pack_into('<QQ',self.r,8,1,2);struct.pack_into('<Q',self.r,0x50,88)
        self.manager=bytearray(0x30);struct.pack_into('<Q',self.manager,0x28,99);self.events=[]
        self.kw=dict(records=self.records,bodies=self.bodies,base_tables=(10,20),final_tables=(30,40),
            get_callback_manager=lambda:5,managers={5:self.manager},invoke=self.invoke,release=self.release)

    def tables(self):return tuple(struct.unpack_from('<Q',self.r,o)[0] for o in (0,0x40))
    def invoke(self,*args):self.events.append(('callback',args,self.tables(),bytes(self.r[0x20:0x40])))
    def release(self,t):self.events.append(('free',t,self.tables()))

    def test_detach_then_callback_then_final_tables_then_release(self):
        self.fixture();self.r[0x5a]=1;attach_pose_endpoint_rings(7,2,records=self.records,bodies=self.bodies)
        self.assertEqual(destroy_pose_constraint(7,1,**self.kw),7)
        self.assertEqual(self.events,[('callback',(99,7,1,88),(10,20),bytes(32)),('free',7,(30,40))])
        self.assertTrue(all(struct.unpack_from('<Q',b,0x90)[0]==0 for b in self.bodies.values()))

    def test_flags_and_callback_gates(self):
        for flags in range(8):
            self.fixture();self.kw['get_callback_manager']=lambda:self.fail('disabled callback reads manager')
            destroy_pose_constraint(7,flags,**self.kw)
            self.assertEqual(self.events,[('free',7,(30,40))] if flags&1 and not flags&4 else [])
        self.fixture();self.r[0x5a]=1;struct.pack_into('<Q',self.manager,0x28,0)
        destroy_pose_constraint(7,0,**self.kw);self.assertEqual(self.events,[])

    def test_body_removal_composes_with_destructor(self):
        self.fixture();self.r[0x5a]=1;provider=bytearray(0x90);arrays={100:[0]*8,200:[0]*8}
        for off,ptr in ((0x60,100),(0x70,200)):struct.pack_into('<QII',provider,off,ptr,0,8)
        metadata={11:bytearray(0x60),12:bytearray(0x60)}
        for b,m in ((1,11),(2,12)):
            struct.pack_into('<Q',self.bodies[b],0x30,m);struct.pack_into('<Q',metadata[m],0x20,b)
        register_pose_constraint(provider,7,arrays=arrays,grow=lambda *a:self.fail('growth'),get_kind=lambda t:4,
            notify=lambda t,s:attach_pose_endpoint_rings(t,s,records=self.records,bodies=self.bodies))
        process_pose_body_constraints(provider,1,None,constraints=self.records,bodies=self.bodies,metadata=metadata,
            arrays=arrays,get_kind=lambda t:4,destroy=lambda t,f:destroy_pose_constraint(t,f,**self.kw),
            grow_output=lambda *a:self.fail('no output'))
        self.assertEqual(struct.unpack_from('<I',provider,0x68)[0],0)
        self.assertEqual(struct.unpack_from('<I',provider,0x78)[0],0)
        self.assertEqual([e[0] for e in self.events],['callback','free'])
        self.assertEqual(self.tables(),(30,40))


if __name__=='__main__':unittest.main()
