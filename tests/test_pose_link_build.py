import copy
import struct
import unittest
import test_pose_link_builder as fixtures
from engine.pose_link_build import build_dispatched_pose_links


class UnifiedBuildTests(unittest.TestCase):
    def fixture(self,mode):
        c,b,p,args=fixtures.BuilderTests().fixture(2)
        c['flags38']=(c['flags38']&~3)|mode;c['pools']={}
        for i,(name,stride) in enumerate((('clear_primary',112),('paired_primary',128),('clear_secondary',112),('paired_secondary',128),('clear_shared',208),('paired_shared',256))):
            c['pools'][name]=dict(count=0,rows=[bytearray([0xa5]*stride) for _ in range(8)],base=0x1000*(i+1))
        bodies={1:copy.deepcopy(b),2:copy.deepcopy(b)}
        bodies[1]['metadata_flags50']=0;bodies[2]['metadata_flags50']=0x8000
        links={};payloads={}
        for k in range(4):
            payloads[k]=copy.deepcopy(p)
            struct.pack_into('<I',payloads[k],0x110,1+k%2)
            for j in range(2):struct.pack_into('<f',payloads[k],0x40+64*j,1+j)
            links[k]=dict(flags84=1,first_body=1,second_body=1+k//2,payload_count=1,payload_slots=[k])
        return c,links,bodies,payloads,args

    def test_mixed_families_share_result_numbering(self):
        c,links,bodies,payloads,args=self.fixture(0)
        build_dispatched_pose_links(c,list(links),links=links,bodies=bodies,payloads=payloads,**args)
        self.assertEqual(c['result_count'],14)
        self.assertEqual([struct.unpack_from('<I',payloads[k],0x44)[0] for k in range(4)],[2,6,8,12])
        for kind in ('clear','paired'):
            self.assertEqual([c['pools'][kind+'_'+name]['count'] for name in ('primary','secondary','shared')],[3,2,1])

    def test_nonzero_mode_uses_single_rows_and_disabled_link_is_skipped(self):
        c,links,bodies,payloads,args=self.fixture(1)
        links[0]['flags84']=0
        build_dispatched_pose_links(c,list(links),links=links,bodies=bodies,payloads=payloads,**args)
        self.assertEqual(c['result_count'],17)
        self.assertEqual(c['pools']['clear_primary']['count'],2)
        self.assertEqual(c['pools']['paired_secondary']['count'],6)
        for kind in ('clear','paired'):self.assertEqual(c['pools'][kind+'_shared']['count'],0)
