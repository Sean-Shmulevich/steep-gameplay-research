import copy
import struct
import unittest
from engine.raw_animation_pose import RawClipPose


def body(tracks):
    header=struct.pack('<QIBfIIII',1,0x0fa3067f,1,1.,1,2,0,0)+bytes(4)+struct.pack('<I',0)
    table=struct.pack('<BQIII',0,0,0x0181efe8,3,len(tracks))
    table+=b''.join(struct.pack('<QII',0,0x653caa76,h) for h,_ in tracks)
    return header+table+struct.pack('<HIII',0,0,5,len(tracks))+b''.join(t for _,t in tracks)


def record(codec,samples,ticks=b'',count=1):
    return struct.pack('<BII',codec,0,count)+ticks+samples


def rig():
    return {'bones':[{'name':'root','binding_hash':7,'parent_index':None,'local_bind':{'translation':[1,0,0],'quaternion_xyzw':[0,0,0,1]}},
                     {'name':'child','binding_hash':8,'parent_index':0,'local_bind':{'translation':[0,2,0],'quaternion_xyzw':[0,0,0,1]}}]}


class RawPoseTests(unittest.TestCase):
    def test_components_bind_fallback_hierarchy_and_scale(self):
        clip=body([(7,record(27,struct.pack('<6f',2,0,0,4,0,0),bytes([60]),2)),(8,record(0,struct.pack('<4f',0,0,0,1)))])
        source=rig();saved=copy.deepcopy(source);adapter=RawClipPose(clip,source,unit_scale=.5)
        pose=adapter.sample(.5,30)
        self.assertEqual(pose['local_pose'][0]['translation'],[1.5,0,0])
        self.assertEqual(pose['local_pose'][1]['translation'],[0,1,0])
        self.assertEqual(pose['model_pose'][1]['translation'],[1.5,1,0])
        self.assertEqual(source,saved)
        rewind=adapter.sample(0,0,cursors=pose['cursors'])
        self.assertEqual(rewind,adapter.sample(0,0))

    def test_auxiliary_and_unknown_do_not_overwrite_bones(self):
        clip=body([(7,record(54,struct.pack('<I',123))),(99,record(27,struct.pack('<3f',9,9,9)))])
        pose=RawClipPose(clip,rig(),unit_scale=1).sample(0,0)
        self.assertEqual(pose['local_pose'][0]['translation'],[1,0,0])
        self.assertEqual(pose['diagnostics']['unbound_transform_tracks'],[1])
        self.assertEqual(pose['auxiliary'][0]['value'],[123])

    def test_duplicate_component_and_shared_rejected(self):
        t=record(27,struct.pack('<3f',1,2,3))
        with self.assertRaises(ValueError):RawClipPose(body([(7,t),(7,t)]),rig(),unit_scale=1)
        with self.assertRaises(ValueError):RawClipPose(body([(7,struct.pack('<BI',254,0))]),rig(),unit_scale=1)
        bad=rig();bad['bones'][1]['binding_hash']=7
        with self.assertRaises(ValueError):RawClipPose(body([(7,t)]),bad,unit_scale=1)

    def test_cursor_failure_keeps_input(self):
        adapter=RawClipPose(body([(7,record(54,struct.pack('<I',1)))]),rig(),unit_scale=1)
        cursors=[0];saved=cursors[:]
        with self.assertRaises(ValueError):adapter.sample(0,-1,cursors=cursors)
        self.assertEqual(cursors,saved)
        with self.assertRaises(ValueError):adapter.sample(0,0,cursors=[])
