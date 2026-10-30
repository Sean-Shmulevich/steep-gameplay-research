import struct
import unittest
from engine.pose_constraint_construct import initialize_pose_command_constraint
from engine.pose_constraint_decode import load_pose_constraint_object,deserialize_pose_command_record


def block(tag,payload):return struct.pack('<II',0xecd70000|tag,len(payload)+8)+payload


class FactoryLoadingTests(unittest.TestCase):
    def reader(self,data):
        r=bytearray(0x50);struct.pack_into('<QI',r,0,1000,len(data));struct.pack_into('<QQ',r,0x10,1000,1000)
        struct.pack_into('<QII',r,0x28,2000,0,8);struct.pack_into('<QII',r,0x38,3000,0,8)
        return r,{1000:data}

    def test_default_factory_then_load_keeps_callback_null(self):
        data=block(0x2601,struct.pack('<H',4))+block(0x2607,struct.pack('<IB',0,1))
        reader,buffers=self.reader(data);record=bytearray([0xa5]*0x200);events=[];table=bytearray(128)
        def create(kind):
            events.append(('create',kind));initialize_pose_command_constraint(record,base_tables=(1,2),command_tables=(3,4));return 5000
        def deserialize(t,r):
            events.append(('deserialize',t));deserialize_pose_command_record(record,r,constraint_token=t,
                buffers=buffers,object_tables={2000:table},fixup_arrays={3000:bytearray(192)},
                grow_objects=lambda *a:self.fail('growth'),grow_fixups=lambda *a:self.fail('growth'),bodies={},metadata={})
        self.assertEqual(load_pose_constraint_object(reader,buffers=buffers,create=create,deserialize=deserialize),5000)
        self.assertEqual(events,[('create',4),('deserialize',5000)])
        self.assertEqual(struct.unpack_from('<QI',table,0),(5000,0x9fb9))
        self.assertEqual(struct.unpack_from('<Q',record,0x1f8)[0],0)
        self.assertEqual(record[8:0x40],bytes(0x38));self.assertEqual(record[0x70],1)
        self.assertEqual(record[0x58],0xa5);self.assertEqual(record[0x5a],1)
        self.assertEqual(struct.unpack_from('<4I',record,0x78+48),(0,0xff7fffff,0x7f7fffff,0))

    def test_missing_envelope_and_null_factory(self):
        reader,buffers=self.reader(b'')
        self.assertEqual(load_pose_constraint_object(reader,buffers=buffers,create=lambda k:self.fail('missing'),deserialize=lambda *a:self.fail('missing')),0)
        self.assertEqual(reader[0x20],1)
        reader,buffers=self.reader(block(0x2601,struct.pack('<H',4)))
        with self.assertRaisesRegex(ValueError,'factory returned null'):
            load_pose_constraint_object(reader,buffers=buffers,create=lambda k:0,deserialize=lambda *a:self.fail('null'))


if __name__=='__main__':unittest.main()
