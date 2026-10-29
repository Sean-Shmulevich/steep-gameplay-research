import math
import struct
import unittest
from tests.test_pose_axis_translations import fixture
from engine.pose_constraint_axes import build_pose_axis_constraint,prepare_pose_angular_axes,prepare_pose_axis_constraint
from engine.pose_constraint_build import build_pose_constraints
from engine.snow_pose_solver_counts import pose_solver_counts


def full_fixture(states=(0,0,0),soft=False):
    c,r,args=fixture((1,1,1));c.extend(bytes(0x2000))
    for cat in (18,19,20,21):struct.pack_into('<I',c,0x40+4*cat,0x400+(cat-18)*64)
    for state,off in zip(states,(0x12c,0x140,0x154)):struct.pack_into('<I4f',r,off,state,-.5,.75,4. if soft else 1e12,1.)
    args['atan2']=math.atan2
    return c,r,args


class AxisConstraintTests(unittest.TestCase):
    def test_counts_match_prepass(self):
        import itertools
        for states in itertools.product(range(3),repeat=3):
            for soft in (False,True):
                c,r,args=full_fixture(states,soft)
                for off in (0x168,0x174,0x180):r[off]=1;struct.pack_into('<2f',r,off+4,.5,1.)
                counts=pose_solver_counts(r[0x70:0x190],0)
                build_pose_axis_constraint(c,r,**args)
                for cat,key in ((8,'doubled_rows'),(14,'flagged_or_hard_rows'),(18,'second_hard_rows'),(20,'second_soft_rows')):
                    self.assertEqual(struct.unpack_from('<I',c,0xa4+4*cat)[0],counts[key])

    def test_submission_preserves_unreserved_angular_states(self):
        from engine.snow_pose_record import prepare_pose_submission
        for state in (3, 0xffffffff):
            for swapped in (0, 1):
                c,r,args=full_fixture((state,1,1))
                # Source and inline layouts differ by 0x20 after the frames.
                source=bytearray(0x100)
                config=r[0x70:0x190]
                for i in range(8):
                    source[12*i:12*i+12]=config[16*i:16*i+12]
                source[0x60:0xd8]=config[0x80:0xf8]
                stored=prepare_pose_submission(source,config,swap_byte=swapped)['storage']
                r[0x70:0x190]=stored
                self.assertEqual(struct.unpack_from('<I',stored,0xbc)[0],state)
                self.assertEqual(pose_solver_counts(stored,0)['doubled_rows'],0)
                build_pose_axis_constraint(c,r,**args)
                self.assertEqual(struct.unpack_from('<I',c,0xa4+4*8)[0],2)

    def test_skip_all_angular_states_avoids_frame_normalization(self):
        c,r,args=full_fixture((1,1,1))
        for b in args['bodies'].values():b[0x40:0x70]=bytes(48)
        build_pose_axis_constraint(c,r,**args)
        self.assertEqual(struct.unpack_from('<I',c,0x180)[0],0)

    def test_each_enabled_drive_can_notify(self):
        c,r,args=full_fixture((1,1,1))
        for off in (0x168,0x174,0x180):r[off]=1;struct.pack_into('<2f',r,off+4,.5,1.)
        struct.pack_into('<Q',args['bodies'][1],0x10,1);struct.pack_into('<Q',args['metadata'][10],0x20,1)
        calls=[];build_pose_axis_constraint(c,r,notify=lambda *x:calls.append(x),**args)
        self.assertEqual(calls,[(1,2)]*3)

    def test_dispatch_matches_complete_builder(self):
        c,r,args=full_fixture((0,1,2),True);d=bytearray(c);rr=bytearray(r)
        build_pose_axis_constraint(c,r,**args)
        build_pose_constraints(d,[1],constraints={1:rr},get_kind=lambda _:2,**args)
        self.assertEqual(c,d);self.assertEqual(r,rr)

    def test_near_parallel_branch_uses_alternate_axis(self):
        c,r,args=full_fixture()
        args.pop('atan2');data=prepare_pose_axis_constraint(r,**args)
        data['axes'][1][0]=data['axes'][0][2][:]
        triples=prepare_pose_angular_axes(data,swapped=False)
        self.assertTrue(all(math.isfinite(x) for triple in triples for vec in triple for x in vec))
