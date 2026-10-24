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

    def test_body_removal_detaches_both_constraint_families(self):
        from engine.pose_body_membership import remove_body_constraints,remove_pose_body
        g=dict(token=9,count=2,capacity=2,slots=[1,2],link_count=2,
               link_slots=[10,11],pose_count=2,pose_slots=[20,21])
        bodies={i:dict(token=i,group=9,index=i-1) for i in (1,2)}
        links={10:dict(first=1,second=2,index=0),11:dict(first=2,second=3,index=1)}
        poses={20:dict(first=2,second=1,index=0,group=9),21:dict(first=2,second=3,index=1,group=9)}
        seen=[]
        def detach(group,token):
            remove_body_constraints(group,token,links=links,poses=poses,
                                    clear_link=lambda item:seen.append(item['index']))
        remove_pose_body(g,bodies[1],bodies=bodies,remove_constraints=detach,invalid_index=0xffffffff)
        self.assertEqual(seen,[0]);self.assertEqual(g['slots'],[2,2])
        self.assertEqual(g['link_slots'],[11,11]);self.assertEqual(g['pose_slots'],[21,21])
        self.assertEqual((g['count'],g['link_count'],g['pose_count']),(1,1,1))
        self.assertEqual(bodies[2]['index'],0);self.assertEqual(poses[21]['index'],0)
        self.assertEqual(poses[20]['group'],0);self.assertEqual(links[10]['index'],0xffffffff)
        self.assertEqual(bodies[1]['group'],0)
