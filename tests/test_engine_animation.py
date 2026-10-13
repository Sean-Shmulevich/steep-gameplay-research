import copy
import math
import unittest
from engine import animation as a

class AnimationTests(unittest.TestCase):
    def setUp(self):
        self.rig, self.clips = a.default_resources()

    def test_idle_hierarchy_and_inputs_unchanged(self):
        state, inputs = {'clip': 'idle', 'time': 0}, {'body': {'velocity': [3,2,1]}}
        before = copy.deepcopy((self.rig, self.clips, state, inputs))
        result = a.evaluate(self.rig, self.clips, state, .1, inputs)
        self.assertAlmostEqual(result['model_pose'][2]['translation'][2], .2)
        self.assertEqual(before, (self.rig, self.clips, state, inputs))

    def test_interpolation_rotation_and_nonloop_endpoint(self):
        result = a.evaluate(self.rig, self.clips, {'clip':'bend', 'time':0}, .5, {})
        self.assertAlmostEqual(result['local_pose'][1]['quaternion_xyzw'][1], math.sin(.175))
        self.assertLess(result['model_pose'][2]['translation'][0], 0)
        result = a.evaluate(self.rig, self.clips, result['state'], 9, {})
        self.assertEqual(result['state']['time'], 1)

    def test_loop_boundary_explicit(self):
        result = a.evaluate(self.rig, self.clips, {'clip':'idle', 'time':.8}, .2, {})
        self.assertEqual(result['state']['time'], 0)
        self.clips['idle']['loop'] = False
        result = a.evaluate(self.rig, self.clips, {'clip':'idle', 'time':.8}, .2, {})
        self.assertEqual(result['state']['time'], 1)

    def test_fade_half_complete_and_zero(self):
        r = a.evaluate(self.rig, self.clips, {}, .1, {'clip':'bend','fade_seconds':.2})
        self.assertEqual(r['diagnostics']['crossfade_weight'], .5)
        self.assertIn('transition', r['state'])
        r = a.evaluate(self.rig, self.clips, r['state'], .1, {})
        self.assertEqual(r['state']['clip'], 'bend')
        self.assertNotIn('transition', r['state'])
        r = a.evaluate(self.rig, self.clips, {}, 0, {'clip':'bend','fade_seconds':0})
        self.assertEqual(r['state']['clip'], 'bend')

    def test_additive_missing_channels_are_identity(self):
        s = {'additive': {'clip':'lean', 'weight':.5}}
        r = a.evaluate(self.rig, self.clips, s, 0, {})
        self.assertAlmostEqual(r['local_pose'][0]['quaternion_xyzw'][1], math.sin(.05))
        self.assertEqual(r['local_pose'][1]['translation'], [0,0,-.4])
        self.assertEqual(r['local_pose'][0]['translation'], [0,0,1])

    def test_missing_binding_diagnostic(self):
        self.clips['idle']['channels']['unknown'] = [{'time':0, **a._identity()}]
        r = a.evaluate(self.rig, self.clips, {}, 0, {})
        self.assertEqual(r['diagnostics']['missing_channels'], {'idle':['unknown']})

    def test_cyclic_and_invalid_parent(self):
        self.rig['bones'][0]['parent_index'] = 2
        with self.assertRaisesRegex(ValueError, 'cyclic'):
            a.validate_resources(self.rig, self.clips)
        self.rig['bones'][0]['parent_index'] = 9
        with self.assertRaises(ValueError):
            a.validate_resources(self.rig, self.clips)

    def test_invalid_keys_quaternion_and_dt(self):
        for dt in [-.1, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                a.evaluate(self.rig, self.clips, {}, dt, {})
        with self.assertRaises(ValueError):
            a.evaluate(self.rig, self.clips, {'time':-.1}, .2, {})
        key = self.clips['bend']['channels']['knee'][1]
        key['time'] = 0
        with self.assertRaises(ValueError):
            a.validate_resources(self.rig, self.clips)
        key['time'] = 1
        key['quaternion_xyzw'] = [0,0,0,0]
        with self.assertRaises(ValueError):
            a.validate_resources(self.rig, self.clips)

    def test_quaternion_sign_equivalent(self):
        self.clips['bend']['channels']['knee'][1]['quaternion_xyzw'] = [0,0,0,-1]
        r = a.evaluate(self.rig, self.clips, {'clip':'bend'}, .5, {})
        self.assertEqual(r['local_pose'][1]['quaternion_xyzw'], [0,0,0,1])

    def test_palette_remap_root_and_origin(self):
        r = a.evaluate(self.rig, self.clips, {}, 0, {})
        identity = [[float(i==j) for j in range(4)] for i in range(4)]
        p = a.palette(self.rig, r['model_pose'], ['missing','foot'], [identity,identity], origin_shift=[1,0,0])
        self.assertEqual(p['joint_map'], [2,2])
        self.assertEqual(p['missing_mesh_joints'], ['missing'])
        self.assertAlmostEqual(p['rows'][0][2][3], .2)
        self.assertEqual(p['rows'][0][0][3], 1)
        p = a.palette(self.rig, r['model_pose'], ['missing'], [identity])
        self.assertEqual(p['rows'], [])

    def test_step_partition_agrees_without_transition(self):
        s = {'clip':'bend'}
        single = a.evaluate(self.rig, self.clips, s, .4, {})
        first = a.evaluate(self.rig, self.clips, s, .2, {})
        second = a.evaluate(self.rig, self.clips, first['state'], .2, {})
        self.assertEqual(single, second)


    def test_recovered_query_tick_preserves_subframe_interpolation(self):
        self.clips['bend']['sampling_policy']='recovered_60hz'
        a1=a.evaluate(self.rig,self.clips,{'clip':'bend','time':0},.101,{})
        a2=a.evaluate(self.rig,self.clips,{'clip':'bend','time':0},.109,{})
        self.assertNotEqual(a1['local_pose'],a2['local_pose'])
        a3=a.evaluate(self.rig,self.clips,{'clip':'bend','time':0},.12,{})
        self.assertNotEqual(a1['local_pose'],a3['local_pose'])
    def test_inclusive_wrap_compatibility(self):
        self.clips['idle']['wrap_policy']='inclusive'
        out=a.evaluate(self.rig,self.clips,{'clip':'idle','time':0},1,{})
        self.assertEqual(out['state']['time'],1)

if __name__ == '__main__':
    unittest.main()
