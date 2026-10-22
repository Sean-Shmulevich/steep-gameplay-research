import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('animation_capture_probe',Path(__file__).resolve().parents[1]/'scripts/animation_capture_probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
class Client:
    def __init__(self,identity=7,found=True,fail=False):
        self.identity=identity;self.found=found;self.fail=fail;self.calls=[]
    def request(self,method,**params):
        self.calls.append((method,params))
        if method=='player.get':return dict(status='completed',result=dict(identity=7))
        if self.fail:return dict(status='failed',result=dict(error='animation_observation_refused'))
        return dict(status='completed',result=dict(identity=self.identity,found=self.found,epoch=len(self.calls)))
class AnimationCaptureProbeTests(unittest.TestCase):
    def test_read_only_and_paired(self):
        c=Client();r=probe.capture_animation(c,samples=3,interval=0)
        self.assertTrue(r['ok']);self.assertEqual(r['matching_player_identity_queries'],3)
        self.assertEqual(r['distinct_epochs'],3)
        self.assertEqual({x[0] for x in c.calls},{'player.get','animation.get_channel'})
        self.assertFalse(r['atomic_snapshot'])
    def test_failure_preserved(self):
        r=probe.capture_animation(Client(fail=True),samples=2,interval=0)
        self.assertFalse(r['ok']);self.assertEqual(len(r['rows']),2)
        self.assertEqual(r['rows'][0]['animation']['result']['error'],'animation_observation_refused')
    def test_identity_mismatch_or_missing_not_success(self):
        for c in [Client(identity=9),Client(found=False)]:
            self.assertFalse(probe.capture_animation(c,samples=1,interval=0)['ok'])
    def test_invalid_bounds_before_io(self):
        for kwargs in [dict(samples=33),dict(samples=0),dict(key=-1),dict(interval=2)]:
            c=Client()
            with self.assertRaises(ValueError):probe.capture_animation(c,**kwargs)
            self.assertEqual(c.calls,[])
    def test_player_replaced_after_pose_excluded(self):
        class Changing(Client):
            def request(self,method,**params):
                result=super().request(method,**params)
                if len(self.calls)==3:result['result']['identity']=8
                return result
        r=probe.capture_animation(Changing(),samples=1,interval=0)
        self.assertEqual(r['found_queries'],1)
        self.assertEqual(r['matching_player_identity_queries'],0)
        self.assertFalse(r['ok'])
    def test_request_timing_brackets_all_three_reads(self):
        c=Client();r=probe.capture_animation(c,samples=1,interval=0);row=r['rows'][0]
        self.assertEqual([x[0] for x in c.calls],['player.get','animation.get_channel','player.get'])
        self.assertGreaterEqual(row['request_span_seconds'],0)
        self.assertGreaterEqual(row['wall_end_ns'],row['wall_begin_ns'])
    def test_summary_handles_quaternion_sign_and_identity_boundaries(self):
        import copy
        r=probe.capture_animation(Client(),samples=3,interval=0)
        for i,row in enumerate(r['rows']):
            for field in ['player','player_after']:
                row[field]['result'].update(position=[i,0,0],linear_velocity=[3,4,0])
            row['animation']['result'].update(vector=[i,0,0,0],rotation=[0,0,0,(-1)**i])
        summary=probe.summarize_animation(r)
        self.assertEqual(summary['max_local_rotation_delta_radians'],0)
        self.assertEqual(summary['max_body_position_delta'],1)
        self.assertEqual(summary['max_body_speed'],5)
        changed=copy.deepcopy(r)
        for field in ['player','animation','player_after']:changed['rows'][1][field]['result']['identity']=8
        self.assertEqual(probe.summarize_animation(changed)['adjacent_same_identity_pairs'],0)
