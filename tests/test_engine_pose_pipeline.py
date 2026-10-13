import copy
import math
import unittest
from engine.animation import default_resources
from engine.pose_pipeline import apply
from engine.inspection import compare_poses
from reference.skeleton import rotate


class PosePipelineTests(unittest.TestCase):
    def setUp(self):
        self.rig, _ = default_resources()
        self.pose = [copy.deepcopy(b['local_bind']) for b in self.rig['bones']]

    def test_model_orientation_keeps_target_and_moves_descendants(self):
        q = [0, math.sqrt(.5), 0, math.sqrt(.5)]
        result = apply(self.rig, self.pose, [
            dict(kind='orientation', bone='root', frame='local', target=q, weight=1),
            dict(kind='orientation', bone='knee', frame='model', target=[0,0,0,1], weight=1)])
        actual = rotate(result['model_pose'][1]['quaternion_xyzw'], [0,0,1])
        self.assertAlmostEqual(actual[0], 0, places=6)
        self.assertAlmostEqual(actual[2], 1, places=6)
        self.assertAlmostEqual(result['model_pose'][2]['translation'][0], -.4, places=6)

    def test_order_is_explicit_and_inputs_not_mutated(self):
        stages = [dict(kind='orientation', bone='root', frame='local', target=[0,0,1,0], weight=1),
                  dict(kind='orientation', bone='root', frame='local', target=[1,0,0,0], weight=1)]
        state = {'phase': 2}
        before = copy.deepcopy((self.rig, self.pose, stages, state))
        a = apply(self.rig, self.pose, stages, state)
        b = apply(self.rig, self.pose, stages[::-1], state)
        self.assertGreater(compare_poses(a['model_pose'], b['model_pose'])['max_rotation_error_radians'], 3)
        a['state']['phase'] = 7
        self.assertEqual((self.rig, self.pose, stages, state), before)

    def test_landing_alignment_rotates_chain_without_changing_local_lengths(self):
        result = apply(self.rig, self.pose, [dict(kind='landing_alignment', bone='root', source=[0,0,1],
            target=[1,0,0], elapsed=1, horizon=1, minimum_horizon=0)])
        self.assertEqual(result['diagnostics'][0]['weight'], 1)
        self.assertAlmostEqual(result['model_pose'][2]['translation'][0], -.8)
        self.assertEqual(result['local_pose'][1]['translation'], self.pose[1]['translation'])

    def test_antiparallel_landing_retains_recovered_noop(self):
        result = apply(self.rig, self.pose, [dict(kind='landing_alignment', bone='root', source=[0,0,1],
            target=[0,0,-1], elapsed=1, horizon=1, minimum_horizon=0)])
        self.assertEqual(result['local_pose'], self.pose)

    def test_limb_target_does_not_fabricate_complete_ik(self):
        stage = dict(kind='limb_target', root='root', middle='knee', end='foot',
                     requested_middle=[.2,0,.6], requested_end=[0,0,.2], middle_weight=.5,
                     alignment_control=0, end_weight=0, mix_bias=0)
        result = apply(self.rig, self.pose, [stage])
        self.assertEqual(result['local_pose'], self.pose)
        self.assertEqual(result['diagnostics'][0]['status'], 'target_only')
        self.assertGreater(result['diagnostics'][0]['result']['target'][0], 0)

    def test_missing_binding_is_reported(self):
        result = apply(self.rig, self.pose, [dict(kind='orientation', bone='unknown', frame='local',
                                               target=[0,0,0,1], weight=1)])
        self.assertEqual(result['diagnostics'][0]['missing_bindings'], ['unknown'])
        self.assertEqual(result['local_pose'], self.pose)

    def test_invalid_chain_and_implicit_frame_rejected(self):
        with self.assertRaises(ValueError):
            apply(self.rig, self.pose, [dict(kind='orientation', bone='root', target=[0,0,0,1], weight=1)])
        with self.assertRaises(ValueError):
            apply(self.rig, self.pose, [dict(kind='limb_target', root='root', middle='foot', end='knee')])

    def test_non_parent_first_hierarchy_supported(self):
        # Named model-space writes cannot rely on bone 0 being the root.
        reordered = copy.deepcopy(self.rig)
        reordered['bones'] = [reordered['bones'][2], reordered['bones'][0], reordered['bones'][1]]
        for bone, parent in zip(reordered['bones'], [2, -1, 1]):
            bone['parent_index'] = parent
        pose = [b['local_bind'] for b in reordered['bones']]
        result = apply(reordered, pose, [dict(kind='orientation', bone='knee', frame='model', target=[0,0,0,1], weight=1)])
        self.assertAlmostEqual(result['model_pose'][0]['translation'][2], .2)


if __name__ == '__main__':
    unittest.main()
