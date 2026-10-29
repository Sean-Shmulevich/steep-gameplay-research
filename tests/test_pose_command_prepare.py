import struct
import unittest
from engine.pose_command_prepare import prepare_pose_command_constraint,initialize_pose_command_storage
from engine.pose_constraint_commands import build_pose_command_constraint


class CommandPrepareTests(unittest.TestCase):
    def fixture(self):
        r=bytearray([0xa5]*0x200);struct.pack_into('<2Q',r,8,1,2)
        struct.pack_into('<Q',r,0x50,9);r[0x59]=0;struct.pack_into('<Q',r,0x1f8,8)
        bodies={1:bytearray(0x40),2:bytearray(0x40)}
        for token,b in bodies.items():
            struct.pack_into('<Q',b,0x30,token+10);struct.pack_into('<H',b,0x1c,token)
        return r,bodies,{11:bytearray(0x60),12:bytearray(0x60)}

    def test_defaults(self):
        raw=bytearray([0xa5]*400);initialize_pose_command_storage(raw)
        for i in range(6):
            self.assertEqual(raw[i*64:i*64+48],bytes(48))
            self.assertEqual(struct.unpack_from('<4I',raw,i*64+48),(0,0xff7fffff,0x7f7fffff,0))
        self.assertEqual(raw[384:],bytes([0xa5]*16))

    def test_gate_preserves_count_and_does_not_read_second(self):
        r,b,m=self.fixture();m[11][0x52]=1;struct.pack_into('<Q',r,0x10,999)
        old=bytes(r)
        self.assertFalse(prepare_pose_command_constraint(r,reciprocal=4.,bodies=b,metadata=m,
                         invoke=lambda *x:self.fail('gated')))
        self.assertEqual(bytes(r),old)
        struct.pack_into('<Q',r,0x10,2);m[11][0x52]=0;m[12][0x52]=1
        self.assertFalse(prepare_pose_command_constraint(r,reciprocal=4.,bodies=b,metadata=m,
                         invoke=lambda *x:self.fail('gated')))

    def test_callback_to_builder_swap_and_count_reset(self):
        for count in (0,1,6,7,0xffffffff):
            r,b,m=self.fixture();r[0x59]=255;events=[]
            def invoke(fn,first,second,commands,count_out,scalar,mode,user):
                events.append((fn,first,second,scalar,mode,user))
                struct.pack_into('<I',count_out,0,count)
                for i in range(96):struct.pack_into('<I',commands,4*i,i)
            prepare_pose_command_constraint(r,reciprocal=4.,bodies=b,metadata=m,invoke=invoke)
            self.assertEqual(events,[(8,2,1,4.,1,9)])
            expected=count if count<=6 else 0
            self.assertEqual(struct.unpack_from('<I',r,0x74)[0],expected)
            arena=bytearray(0x1000);struct.pack_into('<I',arena,0x16c,0x400)
            build_pose_command_constraint(arena,r,bodies=b)
            self.assertEqual(struct.unpack_from('<I',arena,0x424)[0],expected)
            if expected:self.assertEqual(arena[0x430:0x43c],r[0x90:0x9c])

    def test_construction_callback_mode_order_and_no_count_reset(self):
        from engine.pose_command_prepare import construct_pose_command_constraint
        r,b,m=self.fixture();events=[]
        struct.pack_into('<H',m[11],0x50,0x8000)
        def base(token,first,second,owner,request):
            events.append(('base',token,first,second,owner,request))
            struct.pack_into('<2Q',r,8,second,first)
        def invoke(fn,first,second,commands,count,scalar,mode,user):
            events.append(('callback',fn,first,second,scalar,mode,user))
            self.assertEqual(bytes(count),bytes(4))
            self.assertEqual(struct.unpack_from('<4I',commands,48),(0,0xff7fffff,0x7f7fffff,0))
            struct.pack_into('<I',count,0,7)
        construct_pose_command_constraint(r,constraint_token=50,owner_token=60,
            first_body=1,second_body=2,callback_token=8,userdata=9,request_byte=257,
            table=70,secondary_table=80,bodies=b,metadata=m,construct_base=base,invoke=invoke)
        self.assertEqual(events,[('base',50,1,2,60,1),('callback',8,1,2,0.,0,9)])
        self.assertEqual(r[0x59],1);self.assertEqual(r[0x70],0)
        self.assertEqual(struct.unpack_from('<I',r,0x74)[0],7)
        arena=bytearray(0x1000)
        with self.assertRaises(ValueError):build_pose_command_constraint(arena,r,bodies=b)

    def test_null_second_can_be_callback_first_after_swap(self):
        r,b,m=self.fixture();struct.pack_into('<Q',r,0x10,0);r[0x59]=1;seen=[]
        def invoke(fn,a,b,commands,count,scalar,mode,user):
            seen.append((a,b));struct.pack_into('<I',count,0,1)
        prepare_pose_command_constraint(r,reciprocal=4.,bodies=b,metadata=m,invoke=invoke)
        self.assertEqual(seen,[(0,1)])


if __name__=='__main__':unittest.main()
