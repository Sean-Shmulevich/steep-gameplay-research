import unittest
from engine.pose_group_destinations import assign_pose_group_destinations


class DestinationTests(unittest.TestCase):
    def test_preserved_seed_special_and_single_reuse(self):
        c=dict(group410=10);g=dict(token=9,slots=[None,
            dict(metadata=dict(flags8=8)),dict(metadata=dict(flags8=0)),dict(metadata=dict(flags8=0))])
        destinations=[77,0,0,0];seen=[]
        def acquire(c):seen.append('acquire');return 88
        unused=assign_pose_group_destinations(c,g,destinations,count=4,preparation_result=0,
            eligible=lambda c,b:1,acquire_group=acquire)
        self.assertEqual(destinations,[77,10,9,88]);self.assertFalse(unused)
        self.assertEqual(seen,['acquire'])

    def test_unused_reuse_and_nonzero_preparation(self):
        c=dict(group410=10);g=dict(token=9,slots=[dict(metadata=dict(flags8=8))])
        d=[0]
        self.assertTrue(assign_pose_group_destinations(c,g,d,count=1,preparation_result=0,
            eligible=lambda c,b:257,acquire_group=None))
        d=[0]
        self.assertFalse(assign_pose_group_destinations(c,g,d,count=1,preparation_result=0xffffffff,
            eligible=lambda c,b:256,acquire_group=lambda c:88))
        self.assertEqual(d,[88])
