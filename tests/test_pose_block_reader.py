import struct
import unittest
from engine.pose_block_reader import (select_pose_block,read_pose_block_bytes,
                                      deserialize_retained_pose_command)


def block(tag,payload):return struct.pack('<II',0xecd70000|tag,len(payload)+8)+payload


class BlockReaderTests(unittest.TestCase):
    def fixture(self,data):
        reader=bytearray(0x40);struct.pack_into('<QI',reader,0,1000,len(data))
        struct.pack_into('<QQ',reader,0x10,1000,1000)
        return reader,{1000:data}

    def test_skip_then_consume_and_preserve_prior_error(self):
        data=block(1,b'ab')+block(2,b'payload')+block(3,b'end');r,b=self.fixture(data);r[0x20]=7
        self.assertTrue(select_pose_block(r,2,7,2,True,buffers=b));self.assertEqual(r[0x20],7)
        self.assertEqual(read_pose_block_bytes(r,7,buffers=b),b'payload')
        self.assertTrue(select_pose_block(r,3,3,1,True,buffers=b))
        self.assertEqual(read_pose_block_bytes(r,3,buffers=b),b'end')
        with self.assertRaises(ValueError):read_pose_block_bytes(r,1,buffers=b)

    def test_failed_search_preserves_cursors_and_required_controls_error(self):
        data=block(1,b'a')+block(2,b'b');r,b=self.fixture(data);before=bytes(r[0x10:0x20])
        self.assertFalse(select_pose_block(r,2,1,1,False,buffers=b))
        self.assertEqual(r[0x20],0);self.assertEqual(r[0x10:0x20],before)
        self.assertFalse(select_pose_block(r,2,1,0,True,buffers=b));self.assertEqual(r[0x20],1)
        self.assertTrue(select_pose_block(r,2,1,2,False,buffers=b));self.assertEqual(r[0x20],1)

    def test_invalid_headers_fail_even_if_optional(self):
        for data in (struct.pack('<II',0xabcd0001,8),struct.pack('<II',0xecd70001,7),
                     struct.pack('<II',0xecd70001,100),block(1,b'a')):
            r,b=self.fixture(data);before=bytes(r[0x10:0x20])
            self.assertFalse(select_pose_block(r,1,2,1,False,buffers=b))
            self.assertEqual(r[0x20],1);self.assertEqual(r[0x10:0x20],before)
        r,b=self.fixture(b'abc')
        self.assertFalse(select_pose_block(r,1,2,1,False,buffers=b));self.assertEqual(r[0x20],0)

    def test_tag_not_truncated_to_header_width_and_pointer_guard(self):
        r,b=self.fixture(block(1,b'a'))
        self.assertFalse(select_pose_block(r,0x10001,1,1,False,buffers=b))
        struct.pack_into('<Q',r,0x18,999)
        with self.assertRaises(ValueError):select_pose_block(r,1,1,1,False,buffers=b)

    def test_joined_loader_preserves_callback_and_reads_raw_commands(self):
        payload=bytes(range(64));data=block(0x9999,b'x')+block(0x2607,struct.pack('<iB',1,255))+block(0x2608,payload)
        r,b=self.fixture(data);record=bytearray(0x200);struct.pack_into('<Q',record,0x1f8,12345)
        deserialize_retained_pose_command(record,r,buffers=b,read_base=lambda c,r:None)
        self.assertEqual(record[0x78:0xb8],payload);self.assertEqual(record[0x70],1)
        self.assertEqual(struct.unpack_from('<Q',record,0x1f8)[0],12345)
        self.assertEqual(struct.unpack_from('<QQ',r,0x10),(1000+len(data),)*2)
        self.assertEqual(r[0x20],0)


if __name__=='__main__':unittest.main()
