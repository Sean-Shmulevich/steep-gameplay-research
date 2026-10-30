import struct
import unittest
from engine.pose_reference_reader import replay_pose_references,read_pose_reference


class ReferenceReplayTests(unittest.TestCase):
    def fixture(self):
        self.r=bytearray(0x50);self.table=bytearray(48);self.rows=bytearray([0xa5]*72)
        struct.pack_into('<QII',self.r,0x28,100,2,3);struct.pack_into('<QII',self.r,0x38,200,3,3)
        for i in range(3):struct.pack_into('<QI',self.table,i*16,700+i,10)
        for i,(idx,kind,flag) in enumerate(((0,10,1),(1,99,0),(2,10,1))):
            struct.pack_into('<QIIB',self.rows,i*24,500+i,idx,kind,flag)
        self.dest={500+i:bytearray(b'original') for i in range(3)};self.retains=[];self.events=[]
        self.kw=dict(object_tables={100:self.table},fixup_arrays={200:self.rows},destinations=self.dest,
            allocate_scratch=lambda n:self.allocate(n),release_scratch=lambda s:self.events.append('free'),
            grow_fixups=lambda *a:self.fail('no growth'),retain=self.retains.append)
    def allocate(self,n):self.events.append(('allocate',n));return bytearray(n)

    def test_retry_only_processes_remaining_rows(self):
        self.fixture();self.r[0x20]=7;survivors=bytes(self.rows[24:72])
        self.assertFalse(replay_pose_references(self.r,**self.kw))
        self.assertEqual(self.rows[:48],survivors);self.assertEqual(struct.unpack_from('<I',self.r,0x40)[0],2)
        self.assertEqual(self.retains,[700]);self.assertEqual(self.dest[501],bytes(8));self.assertEqual(self.dest[502],bytes(8))
        struct.pack_into('<I',self.table,24,99);struct.pack_into('<I',self.r,0x30,3)
        self.assertTrue(replay_pose_references(self.r,**self.kw))
        self.assertEqual(self.retains,[700,702]);self.assertEqual(struct.unpack_from('<I',self.r,0x40)[0],0)
        self.assertEqual([struct.unpack_from('<Q',v,0)[0] for v in self.dest.values()],[700,701,702])
        self.assertEqual(self.r[0x20],7);self.assertEqual(self.events,[('allocate',72),'free',('allocate',48),'free'])
        self.assertTrue(replay_pose_references(self.r,**self.kw));self.assertEqual(len(self.events),4)

    def test_failed_rows_preserve_full_payload_and_stale_tail(self):
        self.fixture();struct.pack_into('<I',self.r,0x30,0);before=bytes(self.rows)
        self.assertFalse(replay_pose_references(self.r,**self.kw));self.assertEqual(bytes(self.rows),before)
        self.assertEqual(self.retains,[]);self.assertTrue(all(v==bytes(8) for v in self.dest.values()))

    def test_reference_enqueue_then_replay_after_table_population(self):
        self.fixture();struct.pack_into('<I',self.r,0x30,0);struct.pack_into('<I',self.r,0x40,0)
        payload=struct.pack('<II',0x73cb000a,0);struct.pack_into('<QI',self.r,0,1000,len(payload))
        struct.pack_into('<QQ',self.r,0x10,1000,1008)
        self.assertTrue(read_pose_reference(self.r,self.dest[500],10,destination_token=500,buffers={1000:payload},
            object_tables={100:self.table},fixup_arrays={200:self.rows},grow_fixups=lambda *a:self.fail('capacity'),
            reference_counted=True,retain=self.retains.append))
        self.assertEqual(self.dest[500],b'original')
        struct.pack_into('<I',self.r,0x30,1)
        self.assertTrue(replay_pose_references(self.r,**self.kw));self.assertEqual(self.retains,[700])
        self.assertEqual(struct.unpack_from('<Q',self.dest[500],0)[0],700)


if __name__=='__main__':unittest.main()
