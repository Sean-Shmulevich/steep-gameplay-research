import copy
import math
import unittest
from engine.animation import default_resources
from engine.inspection import inspect_rig, compare_poses, compare_traces


class InspectionTests(unittest.TestCase):
    def test_rig_binding_diagnostics_preserve_provenance(self):
        rig, clips = default_resources()
        rig['provenance'] = 'synthetic'
        rig['bones'][0]['binding_id'] = 7
        rig['bones'][1]['binding_id'] = 7
        clips['idle']['provenance'] = 'video-estimated substitute'
        clips['idle']['channels']['missing'] = [dict(time=0, **rig['bones'][0]['local_bind'])]
        before = copy.deepcopy((rig, clips))
        report = inspect_rig(rig, clips)
        self.assertEqual(report['bone_count'], 3)
        self.assertEqual(report['duplicate_binding_ids'][0]['bone_indices'], [0, 1])
        self.assertEqual(report['clips']['idle']['unknown_channels'], ['missing'])
        self.assertEqual(report['clips']['idle']['provenance'], 'video-estimated substitute')
        self.assertFalse(report['provenance_verified'])
        self.assertEqual((rig, clips), before)

    def test_invalid_hierarchy_reported(self):
        rig, clips = default_resources()
        rig['bones'][0]['parent_index'] = 2
        self.assertIn('cyclic', inspect_rig(rig, clips)['validation_errors'][0])

    def test_pose_sign_translation_and_missing_joint(self):
        pose = {'translation': [0, 0, 0], 'quaternion_xyzw': [0, 0, 0, 1]}
        shifted = {'translation': [0, 3, 4], 'quaternion_xyzw': [0, 0, 0, -2]}
        result = compare_poses({'root': pose, 'foot': pose}, {'root': shifted})
        self.assertEqual(result['missing_in_b'], ['foot'])
        self.assertEqual(result['max_translation_error'], 5)
        self.assertEqual(result['max_rotation_error_radians'], 0)

    def test_rotation_angle_and_zero_rejection(self):
        a = {'translation': [0, 0, 0], 'quaternion_xyzw': [0, 0, 0, 1]}
        b = dict(a, quaternion_xyzw=[0, 0, 1, 0])
        self.assertAlmostEqual(compare_poses([a], [b])['max_rotation_error_radians'], math.pi)
        with self.assertRaises(ValueError):
            compare_poses([a], [dict(a, quaternion_xyzw=[0, 0, 0, 0])])

    def test_trace_alignment_sign_equivalence_and_state_changes(self):
        first = {'tick': 1, 'body': {'orientation': [0, 0, 0, 1]}, 'state': {'grounded': True}}
        same = copy.deepcopy(first)
        same['body']['orientation'] = [0, 0, 0, -1]
        self.assertTrue(compare_traces([first], [same])['equal'])
        same['state']['grounded'] = False
        report = compare_traces([first, {'tick': 3}], [{'tick': 2}, same])
        self.assertEqual(report['missing_in_a'], [2])
        self.assertEqual(report['missing_in_b'], [3])
        self.assertEqual(report['first_difference_tick'], 1)
        self.assertEqual(report['different_ticks'][0]['differences'][0]['path'], '/state/grounded')

    def test_duplicate_ticks_rejected(self):
        with self.assertRaises(ValueError):
            compare_traces([{'tick': 1}, {'tick': 1}], [])

    def test_nonfinite_in_unmatched_tick_rejected(self):
        with self.assertRaises(ValueError):
            compare_traces([{'tick': 1, 'body': {'position': [float('inf'), 0, 0]}}], [])


if __name__ == '__main__':
    unittest.main()
