import struct
import unittest
import test_pose_link_build as fixtures
from test_pose_primary_solver import data
from engine.pose_link_counts import count_pose_link_rows
from engine.pose_solver_layout import plan_pose_solver_layout,initialize_pose_solver_storage
from engine.pose_link_arena import build_and_solve_pose_links


class LinkArenaTests(unittest.TestCase):
    def test_count_layout_build_and_solve_share_retained_storage(self):
        for mode in (0,1):
            c,links,bodies,payloads,args=fixtures.UnifiedBuildTests().fixture(mode)
            for payload in payloads.values():
                for i in range(struct.unpack_from('<I',payload,0x110)[0]):
                    struct.pack_into('<f',payload,0x38+64*i,-2)
            counts=[0]*25
            count_pose_link_rows(counts,list(links),links=links,bodies=bodies,payloads=payloads,mode=mode)
            plan=plan_pose_solver_layout(counts,8);arena=bytearray([0xa5]*plan['size'])
            initialize_pose_solver_storage(arena,counts,8)
            struct.pack_into('<I',arena,0x38,c['flags38'])
            for field,offset in (('scalar_c',0xc),('factor14',0x14),('field1c',0x1c),('field20',0x20)):
                struct.pack_into('<f',arena,offset,c[field])
            state={7:bytearray(32)}
            build_and_solve_pose_links(arena,list(links),links=links,bodies=bodies,payloads=payloads,
                                      body_data={7:data()},body_state=state,**args)
            self.assertEqual(struct.unpack_from('<I',arena,0x180)[0],sum(counts))
            for category in (0,1,4,5,6,7):
                self.assertEqual(struct.unpack_from('<I',arena,0xa4+4*category)[0],counts[category])
            indices=[struct.unpack_from('<I',p,0x44)[0] for p in payloads.values()]
            self.assertEqual(len(set(indices)),4)
            self.assertTrue(all(i<sum(counts) for i in indices))
            self.assertNotEqual(state[7],bytes(32))

    def test_missing_arena_is_rejected(self):
        with self.assertRaises(ValueError):
            build_and_solve_pose_links(bytearray(20),[],links={},bodies={},payloads={},resources={},profiles={},modes={},body_data={},body_state={})
