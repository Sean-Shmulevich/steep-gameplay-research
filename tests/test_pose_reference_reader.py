import struct
import unittest
from engine.pose_reference_reader import read_pose_reference
from engine.pose_block_reader import select_pose_block


class ReferenceReaderTests(unittest.TestCase):
    def fixture(self,index,marker=0x73cb9fb6):
        payload=struct.pack('<II',marker,index);self.reader=bytearray(0x50)
        struct.pack_into('<QI',self.reader,0,1000,8);struct.pack_into('<QQ',self.reader,0x10,1000,1008)
        struct.pack_into('<QII',self.reader,0x28,2000,1,1);struct.pack_into('<QII',self.reader,0x38,3000,0,0)
        self.dest=bytearray(b'original');self.table=bytearray(16);struct.pack_into('<QI',self.table,0,77,0x9fb6)
        self.fixups={3000:bytearray()};self.retained=[];self.buffers={1000:payload}
    def grow(self,r,capacity):
        self.fixups[4000]=bytearray([0xa5]*(capacity*24));struct.pack_into('<QII',r,0x38,4000,0,capacity)
    def read(self,counted=False,kind=0x9fb6):
        return read_pose_reference(self.reader,self.dest,kind,destination_token=5000,buffers=self.buffers,
            object_tables={2000:self.table},fixup_arrays=self.fixups,grow_fixups=self.grow,
            reference_counted=counted,retain=self.retained.append)

    def test_forward_reference_growth_preserves_destination_and_padding(self):
        self.fixture(9);self.assertTrue(self.read());self.assertEqual(self.dest,b'original')
        row=self.fixups[4000];self.assertEqual(struct.unpack_from('<QII',row,0),(5000,9,0x9fb6))
        self.assertEqual(row[16],0);self.assertEqual(row[17:24],bytes([0xa5]*7))
        self.assertEqual(struct.unpack_from('<I',self.reader,0x40)[0],1)

    def test_null_sentinel_differs_for_counted_variant(self):
        self.fixture(0xffffeeee);self.assertTrue(self.read());self.assertEqual(self.dest,bytes(8))
        self.fixture(0xffffeeee);self.assertTrue(self.read(True));self.assertEqual(self.dest,b'original')
        self.assertEqual(self.fixups[4000][16],1);self.assertEqual(self.retained,[])

    def test_type_failures_consume_different_lengths_without_setting_error(self):
        self.fixture(0,0x73cb1234);self.assertFalse(self.read())
        self.assertEqual(struct.unpack_from('<Q',self.reader,0x10)[0],1004)
        self.fixture(0);struct.pack_into('<I',self.table,8,0x1234);self.assertFalse(self.read())
        self.assertEqual(struct.unpack_from('<Q',self.reader,0x10)[0],1008)
        self.assertEqual(self.dest,b'original');self.assertEqual(self.reader[0x20],0)

    def test_counted_publication_precedes_retain(self):
        self.fixture(0)
        def retain(t):
            self.assertEqual(struct.unpack_from('<Q',self.dest,0)[0],t);self.retained.append(t)
        self.assertTrue(read_pose_reference(self.reader,self.dest,0x9fb6,destination_token=5000,
            buffers=self.buffers,object_tables={2000:self.table},fixup_arrays=self.fixups,
            grow_fixups=self.grow,reference_counted=True,retain=retain))
        self.assertEqual(self.retained,[77])

    def test_reference_read_composes_with_block_framing(self):
        self.fixture(0);payload=self.buffers[1000];self.buffers[1000]=struct.pack('<II',0xecd72602,16)+payload
        struct.pack_into('<I',self.reader,8,16);struct.pack_into('<QQ',self.reader,0x10,1000,1000)
        self.assertTrue(select_pose_block(self.reader,0x2602,8,3,True,buffers=self.buffers))
        self.assertTrue(self.read());self.assertEqual(struct.unpack_from('<Q',self.dest,0)[0],77)
        self.assertEqual(struct.unpack_from('<Q',self.reader,0x10)[0],1016)


if __name__=='__main__':unittest.main()
