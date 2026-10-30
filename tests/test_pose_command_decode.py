import struct
import unittest
from engine.pose_command_decode import deserialize_pose_command_constraint
from engine.pose_constraint_commands import build_pose_command_constraint


class CommandDecodeTests(unittest.TestCase):
    def decode(self,record,blocks,select_hook=None):
        state={'index':0,'position':0,'data':b''};events=[]
        def select(reader,tag,size,scan_limit,required):
            events.append((tag,size,scan_limit,required))
            data=blocks[reader['index']];reader['index']+=1
            if select_hook:select_hook(reader['index'],record)
            if data is not None:reader.update(position=0,data=data)
            return data is not None
        def read(reader,n):
            p=reader['position'];reader['position']+=n;return reader['data'][p:p+n]
        deserialize_pose_command_constraint(record,state,read_base=lambda r,s:None,select_block=select,read_bytes=read)
        return events

    def test_missing_blocks_preserve_slots_and_callback(self):
        r=bytearray([0x5a]*0x200);struct.pack_into('<i',r,0x74,2);before=bytes(r)
        data=bytes(range(64));events=self.decode(r,[None,None,data])
        self.assertEqual(r[0x78:0xb8],before[0x78:0xb8]);self.assertEqual(r[0xb8:0xf8],data)
        self.assertEqual(r[0x1f8:],before[0x1f8:]);self.assertEqual(r[0x70],0x5a)
        self.assertEqual(events,[(0x2607,5,3,True),(0x2608,64,3,True),(0x2608,64,3,True)])

    def test_negative_count_and_normalized_flag(self):
        r=bytearray(0x200);self.decode(r,[struct.pack('<iB',-1,255)])
        self.assertEqual(struct.unpack_from('<i',r,0x74)[0],-1);self.assertEqual(r[0x70],1)

    def test_count_reload_and_invalid_inputs(self):
        r=bytearray(0x200)
        def change(i,r):
            if i==2:struct.pack_into('<i',r,0x74,1)
        events=self.decode(r,[struct.pack('<iB',3,0),bytes(64)],change)
        self.assertEqual(len(events),2)
        with self.assertRaisesRegex(ValueError,'capacity'):self.decode(r,[struct.pack('<iB',7,0)])
        with self.assertRaisesRegex(ValueError,'Truncated'):self.decode(r,[b'\0\0'])

    def test_decoded_command_feeds_existing_row_builder(self):
        r=bytearray(0x200);struct.pack_into('<QQ',r,8,1,0)
        payload=struct.pack('<16f',*range(16));self.decode(r,[struct.pack('<iB',1,1),payload])
        c=bytearray(0x1000)
        for off,value in ((0x16c,0x400),(0xa0,0),(0x104,0),(0x180,7)):struct.pack_into('<I',c,off,value)
        body=bytearray(0x40);struct.pack_into('<H',body,0x1c,3)
        self.assertEqual(build_pose_command_constraint(c,r,bodies={1:body}),1)
        self.assertEqual(c[0x430:0x440],payload[:12]+bytes(4))
        self.assertEqual(c[0x470:0x480],payload[48:52]*4)
        self.assertEqual(struct.unpack_from('<I',c,0x180)[0],8)


if __name__=='__main__':unittest.main()
