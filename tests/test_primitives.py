import json
import math
from pathlib import Path
import unittest
from reference import animation_codec as codec, animation_blending as blend, animation_playback as playback, skeleton, snow
from testbench.capture import capture

class CodecTests(unittest.TestCase):
    def test_all_omitted_components(self):
        for omitted in range(4):
            q = codec.quaternion32((omitted << 30) | (511 << 20) | (511 << 10) | 511)
            self.assertEqual(q[omitted], 1.)
            self.assertEqual(sum(x*x for x in q), 1.)
    def test_nonidentity(self):
        q = codec.quaternion32((3 << 30) | (700 << 20) | (400 << 10) | 511)
        self.assertGreater(q[0], 0)
        self.assertLess(q[1], 0)
        self.assertAlmostEqual(sum(x*x for x in q), 1.)
    def test_explicit_duplicates(self):
        self.assertEqual(codec.time_keys(bytes([2,2,8]),4,0), ([0,2,2,8],3))
        self.assertEqual(codec.time_keys(bytes([0,1]),2,1), ([0,256],2))
    def test_mask(self):
        self.assertEqual(codec.time_keys(bytes([66,5,0]),2,2), ([0,4],3))
    def test_bad_frames(self):
        for data,count,fmt in [(b'',2,0),(b'\x01',2,1),(bytes([65,2]),2,2),(bytes([65,1]),2,2)]:
            with self.assertRaises(ValueError): codec.time_keys(data,count,fmt)

class MathTests(unittest.TestCase):
    def test_speed_threshold_units(self):
        self.assertAlmostEqual(snow.preset_weight(7/3.6), 0, places=5)
        self.assertAlmostEqual(snow.preset_weight(12/3.6), 1, places=5)
        self.assertAlmostEqual(snow.preset_weight(9.5/3.6), .5, places=5)
    def test_relative_point_velocity(self):
        self.assertEqual(snow.point_relative_velocity((1,0,0),(0,0,2),(0,1,0),(0,0,0),(0,0,0)),(-1,0,0))
    def test_blend_order_and_masks(self):
        w, dominant = blend.normalize_weights([-1,2,2])
        self.assertEqual(w,[0,.5,.5]); self.assertEqual(dominant,1)
        schedule=blend.incremental_blend_schedule(w)
        self.assertEqual([v['child'] for v in schedule],[1,2])
        self.assertEqual(schedule[-1]['alpha'],.5)
        self.assertEqual(blend.masked_channel_weight(0,1),0)
        self.assertEqual(blend.masked_channel_weight(255,1),1)
    def test_wrap_boundary(self):
        self.assertEqual(playback.inclusive_wrap(1),1)
        self.assertEqual(playback.inclusive_wrap(1.25),.25)
        self.assertEqual(blend.wrap_phase_inclusive(1),1)
    def test_hierarchy_and_lod(self):
        bones=json.loads((Path(__file__).parent/'fixtures/rig.json').read_text())['bones']
        pose=skeleton.native_propagate(bones)
        self.assertEqual(pose[2]['translation'],[1,2,3])
        local=skeleton.native_model_to_local(bones,pose)
        self.assertEqual(local,[b['local_bind'] for b in bones])
        held=skeleton.native_propagate(bones,lod=0,minimum_lod=[0,1,1],descendant_counts=[2,1,0],previous_output=pose)
        self.assertEqual(held,pose)

class CaptureTests(unittest.TestCase):
    def test_identity_swap_rejected(self):
        identities=iter([1,2]); result=capture(lambda:next(identities),lambda:{'x':2},max_groups=1)
        self.assertFalse(result['atomic']);self.assertIsNone(result['rows'][0]['fields'])
    def test_bounds(self):
        self.assertEqual(len(capture(lambda:1,lambda:{},max_groups=3)['rows']),3)
        self.assertEqual(capture(lambda:1,lambda:{},max_seconds=0)['rows'],[])
    def test_deadline_rejects_late_group(self):
        clock=iter([0,0,.2])
        result=capture(lambda:1,lambda:{},max_seconds=.1,clock=lambda:next(clock))
        self.assertFalse(result['rows'][0]['accepted'])
    def test_observation_contract(self):
        data=json.loads((Path(__file__).parents[1]/'data/observations/contact_return.json').read_text())
        self.assertFalse(data['atomic']);self.assertFalse(data['full_capture_cadence_eligible'])
        rows=data['rows'];self.assertGreater(data['source_total_groups'],len(rows))
        self.assertTrue(all(a['source_index']<b['source_index'] for a,b in zip(rows,rows[1:])))
