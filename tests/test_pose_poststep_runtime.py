import struct
import unittest
from tests.test_pose_group_runtime import fixture
from engine.pose_group_runtime import run_pose_group_runtime
from engine.pose_poststep_runtime import make_integrated_pose_poststep
from engine.pose_scalar_trig import scalar_sin_cos


def bind(args,**extra):
    for body in args['bodies'].values():
        if len(body)<0x200:body.extend(bytes(0x200-len(body)))
    def unexpected(*args):raise AssertionError('No resources or body link rings in fixture')
    return make_integrated_pose_poststep(groups=args['groups'],arrays=args['arrays'],
        bodies=args['bodies'],metadata=args['metadata'],links={},clear_link=unexpected,
        entry_arrays={},transforms={},resource_bounds=unexpected,
        half_angle_trig=scalar_sin_cos,**extra)


class PoststepRuntimeTests(unittest.TestCase):
    def test_joined_solve_integrates_and_refreshes_bounds(self):
        arena,plan,args,_=fixture()
        args['poststep']=bind(args)
        original=args['bodies'][1][0x70:0x7c]
        run_pose_group_runtime(arena,**args)
        body=args['bodies'][1];meta=args['metadata'][10]
        self.assertNotEqual(body[0x70:0x7c],original)
        self.assertEqual(meta[4:16],body[0x70:0x7c])
        self.assertEqual(meta[16:28],body[0x70:0x7c])
        self.assertNotEqual(body[0x1a0:0x1ac],bytes(12))

    def test_all_quiet_publishes_inactive_group_flag(self):
        _,_,args,_=fixture();poststep=bind(args)
        poststep(99,1.,1,.5,1.,1.)
        self.assertEqual(args['groups'][99][0xa0],1)
        self.assertEqual([m[0x53]&15 for m in args['metadata'].values()],[2,2])
        self.assertEqual(args['metadata'][10][4:28],bytes(24))

    def test_quiet_override_is_resolved_only_when_check_enabled(self):
        _,_,args,_=fixture();poststep=bind(args)
        struct.pack_into('<Q',args['bodies'][1],0x1c0,500)
        poststep(99,.5,0,1.,1.,1.)
        with self.assertRaisesRegex(ValueError,'quiet override'):
            poststep(99,.5,1,1.,1.,1.)
        poststep=bind(args,quiet_overrides={500:(-1.,-1.,.1)})
        poststep(99,.5,1,1.,1.,1.)
        self.assertEqual(args['metadata'][10][0x53]&15,1)
        self.assertEqual(args['groups'][99][0xa0],0)
