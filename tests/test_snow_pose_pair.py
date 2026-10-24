import unittest
from engine.snow_pose_pair import order_pose_bodies


class PosePairTests(unittest.TestCase):
    def test_flag_precedence_unsigned_keys_and_ties(self):
        a=dict(token=1,flags16=0,key32=0xffffffff)
        b=dict(token=2,flags16=0x8000,key32=0xffffffff)
        self.assertTrue(order_pose_bodies(a,b)['frame_swap'])
        self.assertFalse(order_pose_bodies(b,a)['frame_swap'])
        b['flags16']=0;b['key32']=1
        self.assertEqual(order_pose_bodies(a,b)['tokens'],[2,1])
        b['key32']=a['key32']
        self.assertEqual(order_pose_bodies(a,b)['tokens'],[1,2])

    def test_absence_alias_and_invalid_metadata(self):
        a=dict(token=7,flags16=0xffff,key32=9)
        self.assertEqual(order_pose_bodies(a),dict(tokens=[7,0],keys=[9,0],frame_swap=False))
        self.assertFalse(order_pose_bodies(a,a)['frame_swap'])
        with self.assertRaises(ValueError):order_pose_bodies(a,dict(a,key32=8))
