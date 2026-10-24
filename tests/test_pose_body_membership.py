import unittest
from engine.pose_body_membership import append_pose_body


class BodyMembershipTests(unittest.TestCase):
    def test_zero_capacity_is_not_invented_and_publication_precedes_growth(self):
        group=dict(token=9,count=0,capacity=0,slots=[])
        body=dict(token=7,flags16=0,group=0,index=99);seen=[]
        def grow(g,n):seen.append((n,body['group'],body['index']))
        with self.assertRaises(ValueError):append_pose_body(group,body,grow=grow)
        self.assertEqual(seen,[(0,9,0)])
        self.assertEqual(body['group'],9)

    def test_limit_applies_only_to_high_bit_class(self):
        group=dict(token=9,count=65535,capacity=65536,slots=[0]*65536)
        body=dict(token=7,flags16=0x8000,group=0,index=99)
        self.assertFalse(append_pose_body(group,body,grow=None))
        self.assertEqual(body['group'],0)
        body['flags16']=0
        self.assertTrue(append_pose_body(group,body,grow=None))
        self.assertEqual(body['index'],65535)
        self.assertEqual(group['count'],65536)

    def test_growth_reloads_count_but_keeps_published_index(self):
        group=dict(token=9,count=1,capacity=1,slots=[4]);body=dict(token=7,flags16=0)
        def grow(g,n):g.update(count=0,capacity=n,slots=[0]*n)
        append_pose_body(group,body,grow=grow)
        self.assertEqual(body['index'],1)
        self.assertEqual(group['slots'],[7,0])
