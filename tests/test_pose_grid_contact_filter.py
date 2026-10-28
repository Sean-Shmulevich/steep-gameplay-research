import struct
import unittest
from engine.pose_grid_contact_filter import filter_grid_records

class ContactFilterTest(unittest.TestCase):
    def test_removal_retries_swapped_record_and_preserves_tail(self):
        r=bytearray(0xc0);struct.pack_into('<2H',r,0x68,3,3)
        struct.pack_into('<H',r,0x9c,2);struct.pack_into('<2f',r,0x70,1,1)
        frame=[[1,0,0],[0,1,0],[0,0,1],[0,0,0]]
        records=bytearray(48*4)
        # At vertex0, +X rejects; -X retains. Centroid stays inside.
        for i,(d,p) in enumerate([([1,0,0],[0,0,0]),([-1,0,0],[0,0,0]),([1,0,0],[0,0,0])]):
            struct.pack_into('<3f',records,48*i,*d)
            struct.pack_into('<3f',records,48*i+16,*p)
            struct.pack_into('<I',records,48*i+44,100+i)
        records[144:]=b'T'*48;retained=bytes(records[48:96])
        count=filter_grid_records(r,[0.]*9,frame,0,records,3)
        self.assertEqual(count,1);self.assertEqual(records[:48],retained)
        self.assertEqual(records[144:],b'T'*48)

    def test_empty_does_not_require_geometry(self):
        records=bytearray(b'abc')
        self.assertEqual(filter_grid_records(b'',[],[],0,records,0),0)
        self.assertEqual(records,b'abc')
