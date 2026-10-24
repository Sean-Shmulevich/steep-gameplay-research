import unittest
from engine.pose_group_eligibility import pose_links_clear,pose_group_eligible


class GroupEligibilityTests(unittest.TestCase):
    def test_strict_threshold_and_unconditional_link_query(self):
        calls=[]
        def clear():calls.append(1);return True
        self.assertFalse(pose_group_eligible([1,0,0],[0,0,0],1,1,links_clear=clear))
        self.assertEqual(calls,[1])
        self.assertTrue(pose_group_eligible([.5,0,0],[0,0,0],-1,-1,links_clear=clear))
        self.assertFalse(pose_group_eligible([0]*3,[0]*3,0,1,links_clear=clear))

    def test_endpoint_specific_ring_and_blockers(self):
        links={10:dict(status32=0xffffffff,flags8=0,first_body=7,next_first=20,next_second=99),
               20:dict(status32=0xffffffff,flags8=0,first_body=8,next_first=99,next_second=10)}
        args=dict(body_token=7,blocking_link=0,first_link=10,read_link=links.__getitem__)
        self.assertTrue(pose_links_clear(**args))
        links[20]['flags8']=2;self.assertFalse(pose_links_clear(**args))
        links[20]['flags8']=0;links[20]['next_second']=20
        with self.assertRaises(ValueError):pose_links_clear(**args)
        args['blocking_link']=1;args['read_link']=None
        self.assertFalse(pose_links_clear(**args))
