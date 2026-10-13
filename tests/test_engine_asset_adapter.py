import copy
import unittest
from engine.asset_adapter import from_decoded
from engine.animation import evaluate
from engine.inspection import inspect_rig
class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.rig={'bones':[{'name':'root','binding_hash':7,'parent_index':-1,'local_bind':{'translation':[0,0,0],'quaternion_xyzw':[0,0,0,1]}}]}
        self.clip={'name':'invented','duration':1.,'tracks':[{'binding_hash':7,'value_type':'vector3','values':[[0,0,0],[2,0,0]],'keyframes':[0,60]},{'binding_hash':7,'value_type':'quaternion','values':[[0,0,0,1]],'keyframes':[0]}]}
    def convert(self):return from_decoded(self.rig,[self.clip],unit_scale=.5,looping={'invented':False})
    def test_independent_tracks_and_continuous_interpolation(self):
        bundle=self.convert()['bundle'];pose=evaluate(bundle['rig'],bundle['clips'],{'clip':'invented'},.109,{})
        self.assertAlmostEqual(pose['local_pose'][0]['translation'][0],.109,places=6)
        self.assertEqual(pose['local_pose'][0]['quaternion_xyzw'],[0,0,0,1])
    def test_duplicates_preserved_and_last_tick_wins(self):
        self.clip['tracks'][0].update(keyframes=[0,0,60],values=[[0,0,0],[1,0,0],[2,0,0]])
        bundle=self.convert()['bundle'];pose=evaluate(bundle['rig'],bundle['clips'],{},0,{})
        self.assertEqual(pose['local_pose'][0]['translation'],[.5,0,0])
    def test_unknown_and_auxiliary_diagnostics(self):
        self.clip['tracks'] += [{'binding_hash':99,'value_type':'vector3','values':[[0,0,0]]},{'binding_hash':7,'value_type':'auxiliary_byte','values':[0]}]
        info=self.convert()['diagnostics'];self.assertEqual(len(info['unbound_transform_tracks']),1);self.assertEqual(len(info['auxiliary_tracks']),1)
    def test_policies_and_duplicate_rig_rejected(self):
        with self.assertRaises(ValueError):from_decoded(self.rig,[self.clip],unit_scale=1,looping={})
        self.rig['bones'].append(copy.deepcopy(self.rig['bones'][0]))
        with self.assertRaises(ValueError):self.convert()
    def test_inspection_accepts_separate_streams(self):
        bundle=self.convert()['bundle']
        report=inspect_rig(bundle['rig'],bundle['clips'])
        self.assertEqual(report['validation_errors'],[])
        self.assertEqual(report['clips']['invented']['bound_channels'],['root'])
