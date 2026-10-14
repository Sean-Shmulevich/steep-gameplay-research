import copy
import json
import struct
import unittest
from engine.raw_animation_pose import RawClipPose
from engine.runtime import Engine
from engine.replay import record, replay
from engine import animation, graph
from tests.test_raw_animation_pose import body,record as channel_record,rig


def adapter():
    return RawClipPose(body([(7,channel_record(27,struct.pack('<6f',2,0,0,4,0,0),bytes([60]),2))]),rig(),unit_scale=.5)


class RawRuntimeTests(unittest.TestCase):
    def test_json_bundle_matches_direct_pose(self):
        raw=adapter();bundle=json.loads(json.dumps(raw.engine_bundle(name='sample',loop=False)))
        pose=animation.evaluate(bundle['rig'],bundle['clips'],{},.5,{})
        direct=raw.sample(.5,30)
        self.assertEqual(pose['local_pose'],direct['local_pose'])
        self.assertEqual(pose['model_pose'],direct['model_pose'])
        self.assertEqual(pose['diagnostics']['sampling_policy'],'raw_channels')

    def test_graph_checkpoint_and_replay(self):
        bundle=adapter().engine_bundle(name='sample',loop=True)
        definition={'schema_version':1,'root':'clip','nodes':{'clip':{'type':'clip','clip':'sample'}}}
        scenario={'resources':bundle,'animation':{'graph':definition}}
        engine=Engine(scenario);engine.step(17)
        checkpoint=json.loads(json.dumps(engine.checkpoint()));engine.step(21)
        expected=engine.state_hash();restored=Engine(scenario);restored.restore(checkpoint);restored.step(21)
        self.assertEqual(restored.state_hash(),expected)
        self.assertEqual(replay(record(engine)).state_hash(),expected)
        self.assertEqual(replay(record(restored)).state_hash(),expected)

    def test_graph_blend_and_crossfade_accept_raw_clips(self):
        bundle=adapter().engine_bundle(name='a',loop=False);clips=bundle['clips'];clips['b']=copy.deepcopy(clips['a'])
        definition={'schema_version':1,'root':'blend','nodes':{'a':{'type':'clip','clip':'a'},'b':{'type':'clip','clip':'b'},'blend':{'type':'blend','children':['a','b'],'weights':[.25,.75]}}}
        pose=graph.evaluate_pose(bundle['rig'],clips,{},.5,definition,{})
        expected=adapter().sample(.5,30)
        self.assertEqual(pose['local_pose'],expected['local_pose'])
        start=animation.evaluate(bundle['rig'],clips,{},.2,{})
        end=animation.evaluate(bundle['rig'],clips,start['state'],.1,{'clip':'b','fade_seconds':.1})
        self.assertEqual(end['state']['clip'],'b')

    def test_bad_raw_resources_rejected_atomically(self):
        bundle=adapter().engine_bundle(name='sample',loop=False);engine=Engine({'resources':bundle});before=engine.state_hash()
        for field,value in (('encoding',54),('payload_hex','zz')):
            bad=copy.deepcopy(bundle);bad['clips']['sample']['channels']['root']['translation'][field]=value
            with self.assertRaises(ValueError):engine.replace_resources(bad)
            self.assertEqual(engine.state_hash(),before)
