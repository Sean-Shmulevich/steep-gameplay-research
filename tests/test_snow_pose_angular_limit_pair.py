import struct
import unittest
from engine.snow_pose_angular_row import build_pose_angular_limit_pair
from reference.central_impulse import f32


class AngularLimitPairTests(unittest.TestCase):
    def test_opposite_limits_one_angle_and_headers(self):
        calls=[]
        def angle(y,x):
            calls.append((y,x))
            return .5
        r=build_pose_angular_limit_pair(lower=-.25,upper=.25,
            initial_rows=[b'\xa5'*112]*2,body_indices=[0x12345,0xabcde],
            base_row=2,class_count=0,result_count=0xffffffff,class_byte=1,
            row_region_offset=256,context_scalar=2,context_flags=0x08000000,
            axis=[0,0,1,0],reference=[1,0,0,0],target=[1,0,0,0],atan2=angle)
        self.assertEqual(len(calls),1)
        upper,lower=r['rows']
        self.assertFalse(upper['ungained']);self.assertTrue(lower['ungained'])
        self.assertEqual(struct.unpack_from('<4f',upper['row'],0x10),(f32(-.2),)*4)
        self.assertEqual(struct.unpack_from('<4f',lower['row'],0x10),(1.5,)*4)
        self.assertEqual(struct.unpack_from('<HHI',upper['row']),(0x2345,0xbcde,0xffffffff))
        self.assertEqual(struct.unpack_from('<HHI',lower['row']),(0x2345,0xbcde,0))
        self.assertEqual(lower['relative_offset']-upper['relative_offset'],112)
        self.assertEqual(r['next_result_count'],1)
        self.assertEqual(struct.unpack_from('<f',upper['row'],0x38)[0],-1)
        self.assertEqual(struct.unpack_from('<f',lower['row'],0x38)[0],1)

    def test_inverted_bounds_are_not_repaired(self):
        r=build_pose_angular_limit_pair(lower=1,upper=-1,
            initial_rows=[bytes(128)]*2,body_indices=[0,1],base_row=0,
            class_count=0,result_count=0,class_byte=0,row_region_offset=0,
            context_scalar=1,context_flags=0,axis=[0,0,1,0],
            reference=[1,0,0,0],target=[1,0,0,0],atan2=lambda y,x:0.)
        self.assertEqual([x['residual'] for x in r['rows']],[[-1.]*4]*2)
        self.assertTrue(all(not x['ungained'] for x in r['rows']))
