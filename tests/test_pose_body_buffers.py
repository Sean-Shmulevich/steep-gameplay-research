import struct
import unittest
from engine.pose_body_buffers import build_pose_body_buffers

class BodyBufferTests(unittest.TestCase):
    def body(self):
        return dict(metadata_flags52=0,flagsaa=0,basis=[[1,0,0],[0,1,0],[0,0,1]],
                    tensor170=[[2,0,0],[0,3,0],[0,0,4]],scalar124=.5,
                    motion1a0=[1,2,3],motion1ac=[4,5,6],damping1b8=None)

    def test_identity_tensor_external_increment_and_scalar(self):
        out=build_pose_body_buffers([self.body()],scalar=2,vector=[0,0,-1])
        self.assertEqual(struct.unpack('<16f',out['body_data'][0]),(2,0,0,0,0,3,0,0,0,0,4,0,.5,.5,.5,.5))
        self.assertEqual(struct.unpack('<8f',out['body_state'][0]),(1,2,1,0,4,5,6,0))

    def test_body_flag_suppresses_vector_only(self):
        b=self.body();b['flagsaa']=8
        out=build_pose_body_buffers([b],scalar=2,vector=[0,0,-1])
        self.assertEqual(struct.unpack('<8f',out['body_state'][0]),(1,2,3,0,4,5,6,0))
        self.assertEqual(struct.unpack_from('<f',out['body_data'][0],0x30)[0],.5)

    def test_metadata_gate_suppresses_tensor_scalar_and_state_processing(self):
        b=self.body();b['metadata_flags52']=8;b.pop('tensor170');b.pop('scalar124');b['damping1b8']=[.2]*4
        out=build_pose_body_buffers([b],scalar=2,vector=[0,0,-1])
        self.assertEqual(out['body_data'][0],bytes(64))
        self.assertEqual(struct.unpack('<8f',out['body_state'][0]),(1,2,3,0,4,5,6,0))

    def test_damping_service_receives_base_and_applies_fourth_lane_to_angular(self):
        b=self.body();b['damping1b8']=[.5]*4;calls=[]
        def service(base,scalar):calls.append((base,scalar));return [1,2,3,4]
        out=build_pose_body_buffers([b],scalar=2,vector=[0,0,-1],damping_response=service)
        self.assertEqual(calls,[([.5]*4,2)])
        self.assertEqual(struct.unpack('<8f',out['body_state'][0]),(1,4,3,0,16,20,24,0))
        with self.assertRaises(ValueError):build_pose_body_buffers([b],scalar=2,vector=[0,0,-1])
        build_pose_body_buffers([b],scalar=0,vector=[0,0,-1])

    def test_empty_body_array(self):
        self.assertEqual(build_pose_body_buffers([],scalar=1,vector=[0,0,0]),dict(body_data=[],body_state=[]))
