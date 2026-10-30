import struct
import unittest
from engine.pose_constraint_construct import construct_pose_constraint_base
from engine.pose_command_prepare import construct_pose_command_constraint


class BaseConstructTests(unittest.TestCase):
    def fixture(self,p1,p2,k1,k2):
        self.r=bytearray([0xa5]*0x200);self.bodies={i:bytearray(0x40) for i in (1,2)}
        self.metadata={i:bytearray(0x60) for i in (11,12)};self.visits=[]
        for b,m,p,k in ((1,11,p1,k1),(2,12,p2,k2)):
            struct.pack_into('<Q',self.bodies[b],0x30,m);struct.pack_into('<H',self.metadata[m],0x50,p*0x8000)
            struct.pack_into('<I',self.metadata[m],0x54,k)
    def base(self,t,a,b,owner,flag):
        return construct_pose_constraint_base(self.r,constraint_token=t,first_body=a,second_body=b,owner_token=owner,
            request_byte=flag,tables=(100,200),bodies=self.bodies,metadata=self.metadata,visit_body=self.visits.append)

    def test_priority_then_unsigned_key_and_stable_ties(self):
        for p1,p2,k1,k2,expected in ((0,1,1,99,(2,1)),(1,0,99,1,(1,2)),
                (1,1,0xffffffff,1,(2,1)),(0,0,7,7,(1,2))):
            self.fixture(p1,p2,k1,k2);self.assertEqual(self.base(9,1,2,77,1),9)
            self.assertEqual(struct.unpack_from('<QQ',self.r,8),expected)
            self.assertEqual(struct.unpack_from('<II',self.r,0x18),(k1,k2) if expected==(1,2) else (k2,k1))
            self.assertEqual(self.visits,[1,2] if p1 and p2 else [])
            self.assertEqual(self.r[0x59:0x5b],b'\0\1')
            self.assertEqual(self.r[0x4c:0x50],bytes([0xa5]*4));self.assertEqual(self.r[0x58],0xa5)

    def test_null_second_and_low_request_byte(self):
        self.fixture(1,1,5,6);self.base(9,1,0,77,1)
        self.assertEqual(struct.unpack_from('<QQII',self.r,8),(1,0,5,0));self.assertEqual(self.visits,[])
        self.fixture(1,1,5,6);self.base(9,1,2,77,256);self.assertEqual(self.visits,[])

    def test_specialized_callback_restores_requested_order(self):
        self.fixture(0,1,1,2);calls=[]
        def invoke(fn,a,b,commands,count,scalar,mode,user):
            calls.append((fn,a,b,scalar,mode,user));struct.pack_into('<I',count,0,7)
        construct_pose_command_constraint(self.r,constraint_token=9,owner_token=77,first_body=1,second_body=2,
            callback_token=88,userdata=99,request_byte=1,table=300,secondary_table=400,bodies=self.bodies,
            metadata=self.metadata,construct_base=self.base,invoke=invoke)
        self.assertEqual(struct.unpack_from('<QQ',self.r,8),(2,1));self.assertEqual(self.r[0x59],1)
        self.assertEqual(calls,[(88,1,2,0.,0,99)]);self.assertEqual(self.r[0x70],1)
        self.assertEqual(struct.unpack_from('<I',self.r,0x74)[0],7);self.assertEqual(self.r[0x5a],1)


if __name__=='__main__':unittest.main()
