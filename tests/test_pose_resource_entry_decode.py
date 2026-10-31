import struct
import unittest
from engine.pose_resource_entry_decode import deserialize_pose_resource_entry


class ResourceEntryTests(unittest.TestCase):
    def run_entry(self,flags,priority=0x8000,body_flags=0,index=0):
        payload=struct.pack('<II',0x73cb9fb7,index)+bytes(range(48))+bytes(range(36))+bytes(flags)
        data=struct.pack('<II',0xecd70e03,len(payload)+8)+payload
        entry=bytearray([0xa5]*72);entry[0x44]=0xc0
        body=bytearray(0x200);struct.pack_into('<Q',body,0x30,2)
        meta=bytearray(0x60);struct.pack_into('<H',meta,0x50,priority);meta[0x52]=body_flags
        reader=bytearray(0x50);struct.pack_into('<QI',reader,0,1000,len(data));struct.pack_into('<QQ',reader,0x10,1000,1000)
        table=bytearray(128);struct.pack_into('<QI',table,0,700,0x9fb7)
        struct.pack_into('<QII',reader,0x28,3,1,8);struct.pack_into('<QII',reader,0x38,4,0,8)
        fixups=bytearray(192);events=[]
        deserialize_pose_resource_entry(entry,reader,body,entry_token=200,buffers={1000:data},metadata={2:meta},
            object_tables={3:table},fixup_arrays={4:fixups},grow_fixups=lambda *a:self.fail('growth'),
            set_transform=lambda e,f:events.append((bytes(e),f)))
        return entry,reader,fixups,events

    def test_legacy_default_uses_full_first_byte_before_masking(self):
        for first,priority,body_flags,expected in ((0,0x8000,0,0),(0,0,0,1),(0,0x8000,8,1),(2,0x8000,0,1)):
            e,r,_,events=self.run_entry([first,0,0],priority,body_flags)
            self.assertEqual((e[0x44]>>2)&1,expected)
            self.assertEqual(e[0x44]&1,1)
            self.assertEqual(e[0x44]&2,0)
            self.assertEqual(e[0x44]&0xc0,0xc0)
            self.assertEqual(events[0][1],bytes(range(48)))
            self.assertEqual(events[0][0],e)

    def test_explicit_flags_override_fallback_and_use_low_bits(self):
        e,r,_,_=self.run_entry([3,2,5,7,2,0],priority=0)
        self.assertEqual(e[0x44],0xc0|2|16|32)
        self.assertEqual(e[0x20:0x44],bytes(range(36)))
        self.assertEqual(struct.unpack_from('<Q',e,16)[0],700)
        self.assertEqual(e[:16],b'\xa5'*16)
        self.assertEqual(e[0x18:0x20],b'\xa5'*8)
        self.assertEqual(r[0x20],0)

    def test_short_block_preserves_entry_and_forward_ref_preserves_old_pointer(self):
        e,r,_,events=self.run_entry([0,0])
        self.assertEqual(r[0x20],1);self.assertEqual(events,[])
        self.assertEqual(e[:0x44],b'\xa5'*0x44)
        e,r,fixups,events=self.run_entry([0,0,0],index=12)
        self.assertEqual(e[16:24],b'\xa5'*8)
        self.assertEqual(struct.unpack_from('<QII',fixups,0),(216,12,0x9fb7))
        self.assertEqual(struct.unpack_from('<I',r,0x40)[0],1)
        self.assertEqual(len(events),1)
