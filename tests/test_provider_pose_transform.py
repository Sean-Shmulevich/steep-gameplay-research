import math
import struct
import unittest
from engine.motion_pose_history import transform_provider_pose, PoseHistory, advance_pose_history, query_endpoints

def pose(p,q):return struct.pack('<8f',*p,*q)

class ProviderPoseTransformTests(unittest.TestCase):
    def test_rotation_translation_history_query_chain(self):
        local=pose((1,0,0,0),(0,0,0,1))
        provider=pose((10,20,30,0),(0,0,math.sqrt(.5),math.sqrt(.5)))
        transformed=transform_provider_pose(local,provider,already_world=False)
        values=struct.unpack('<8f',transformed)
        for actual,want in zip(values[:3],(10,21,30)):
            self.assertAlmostEqual(actual,want,places=5)
        state=advance_pose_history(PoseHistory(local,local,1),'valid',transformed)
        start,end=query_endpoints(state,(1,0,0))
        self.assertEqual(start,(2,0,0))
        for actual,want in zip(end,(10,22,30)):
            self.assertAlmostEqual(actual,want,places=5)
        self.assertEqual(state.count,2)

    def test_quaternion_order_and_no_normalization(self):
        local=pose((0,0,0,0),(1,0,0,0))
        provider=pose((0,0,0,0),(0,2,0,0))
        result=struct.unpack('<8f',transform_provider_pose(local,provider,already_world=False))
        self.assertEqual(result[4:],(0,0,-2,0))

    def test_direct_branch_preserves_arbitrary_payload_without_provider(self):
        raw=bytes(range(32))
        self.assertIs(transform_provider_pose(raw,None,already_world=True),raw)

    def test_nonfinite_transform_rejected(self):
        identity=pose((0,0,0,0),(0,0,0,1))
        with self.assertRaises(ValueError):
            transform_provider_pose(pose((float('nan'),0,0,0),(0,0,0,1)),identity,already_world=False)
