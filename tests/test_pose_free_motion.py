import struct
import unittest
from engine.pose_free_motion import advance_pose_free_motion


def fixture():
    body=bytearray(0x1c0);meta=bytearray(0x60)
    struct.pack_into('<Q',body,0x30,10)
    struct.pack_into('<6f',body,0x1a0,1,2,3,2,4,6)
    return body,meta,dict(bodies={1:body},metadata={10:meta},scalar=.5,vector=[2,4,-2])


class FreeMotionTests(unittest.TestCase):
    def test_force_then_per_axis_damping_and_angular_w(self):
        body,meta,args=fixture();struct.pack_into('<Q',body,0x1b8,20);calls=[]
        def response(base,scalar):calls.append((base,scalar));return [.5,.25,1,.5]
        advance_pose_free_motion([1],damping_records={20:[.1,.2,.3,.4]},damping_response=response,**args)
        self.assertEqual(struct.unpack_from('<6f',body,0x1a0),(1,1,2,1,2,3))
        self.assertEqual(len(calls),1);self.assertEqual(calls[0][1],.5)

    def test_fixed_body_and_zero_scalar_skip_damping(self):
        for fixed,scalar in ((8,.5),(0,0.)):
            body,meta,args=fixture();meta[0x52]=fixed;args['scalar']=scalar
            struct.pack_into('<Q',body,0x1b8,20);before=bytes(body)
            advance_pose_free_motion([1],**args)
            self.assertEqual(body,before)

    def test_repeated_body_updates_and_force_suppression(self):
        body,_,args=fixture();advance_pose_free_motion([1,1],**args)
        self.assertEqual(struct.unpack_from('<3f',body,0x1a0),(3,6,1))
        body[0xaa]=8;before=bytes(body)
        advance_pose_free_motion([1],**args)
        self.assertEqual(body,before)
