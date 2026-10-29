import itertools
import struct
import unittest
from tests.test_pose_constraint_cone import fixture as cone_fixture
from engine.pose_constraint_axes import build_pose_axis_translations,prepare_pose_axis_constraint
from engine.snow_pose_solver_counts import pose_solver_counts


def fixture(states=(0,0,0),hard=(True,True,True),paired=False):
    c,r,args=cone_fixture(paired=paired)
    r.extend(bytes(0x1a0-len(r)))
    for cat in (14,15,16,17):struct.pack_into('<I',c,0x40+4*cat,0x200+(cat-14)*0x80)
    for i in range(3):
        struct.pack_into('<4f',r,0x80+i*16,*[float(i==j) for j in range(4)])
        struct.pack_into('<4f',r,0xc0+i*16,*[float(i==j) for j in range(4)])
    struct.pack_into('<4f',r,0xb0,0,0,0,0)
    for i,off in enumerate((0xf0,0x104,0x118)):struct.pack_into('<I4f',r,off,states[i],-.5,.75,1e12 if hard[i] else 4.,1.)
    for off in (0x12c,0x140,0x154):struct.pack_into('<I4f',r,off,1,0,0,1e12,1.)
    for off in (0x168,0x174,0x180):r[off]=0
    r[0x18c]=0
    r[0x190:0x19c]=b'\x5a'*12
    args.pop('atan2')
    return c,r,args


class AxisTranslationTests(unittest.TestCase):
    def test_prepass_counts_match_all_translation_combinations(self):
        for states in itertools.product(range(3),repeat=3):
            for hard in itertools.product((False,True),repeat=3):
                c,r,args=fixture(states,hard)
                expected=pose_solver_counts(r[0x70:0x190],0)
                build_pose_axis_translations(c,r,**args)
                for cat,key in ((8,'doubled_rows'),(10,'hard_triple_blocks'),(14,'flagged_or_hard_rows'),(16,'first_soft_rows')):
                    self.assertEqual(struct.unpack_from('<I',c,0xa4+4*cat)[0],expected[key],(states,hard,cat))

    def test_hard_triple_only_updates_first_feedback_index(self):
        c,r,args=fixture();build_pose_axis_translations(c,r,**args)
        self.assertEqual(struct.unpack_from('<I',r,0x190)[0],0)
        self.assertEqual(r[0x194:0x19c],b'\x5a'*8)

    def test_skipped_and_hard_limit_rows_preserve_feedback(self):
        c,r,args=fixture((1,2,0),(True,True,False))
        build_pose_axis_translations(c,r,**args)
        self.assertEqual(r[0x190:0x198],b'\x5a'*8)
        self.assertEqual(struct.unpack_from('<I',r,0x198)[0],2)

    def test_single_second_arm_ignores_center(self):
        c,r,args=fixture(paired=False)
        struct.pack_into('<3f',args['bodies'][2],0x128,5,6,7)
        data=prepare_pose_axis_constraint(r,**args)
        self.assertEqual(data['arms'][1],[0,0,0,0])
        struct.pack_into('<H',args['metadata'][20],0x50,0x8000)
        data=prepare_pose_axis_constraint(r,**args)
        self.assertEqual(data['arms'][1],[-5,-6,-7,0])
