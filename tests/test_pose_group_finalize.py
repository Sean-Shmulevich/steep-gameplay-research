import unittest
from engine.pose_group_finalize import finalize_pose_group


def array(values,capacity=8):return dict(count=len(values),capacity=capacity,slots=values+[0]*(capacity-len(values)))


class FinalizeTests(unittest.TestCase):
    def test_filters_links_transfers_group_and_tracks_bodies(self):
        c=dict(group408=8,group410=10,groups418=array([]),groups428=array([9,11]),
               tracked=array([1]),pending_links=array([]))
        g=dict(token=9,index=0,flag_a0=1,count=2,slots=[1,2],link_count=2,link_slots=[20,21])
        groups={9:g,11:dict(index=1)};bodies={1:dict(metadata=dict(kind8=0x12)),2:dict(metadata=dict(kind8=1))}
        seen=[]
        self.assertTrue(finalize_pose_group(c,g,groups=groups,bodies=bodies,
            links={20:dict(first=1),21:dict(first=2)},virtual40=lambda b:seen.append(b),grow=None))
        self.assertEqual(len(seen),2);self.assertEqual(g['flag_a0'],0)
        self.assertEqual(c['pending_links']['slots'][0],20)
        self.assertEqual(c['tracked']['slots'][:3],[1,1,2])
        self.assertEqual(c['groups428']['slots'][:2],[11,11]);self.assertEqual(groups[11]['index'],0)
        self.assertFalse(finalize_pose_group(c,g,groups=None,bodies=None,links=None,virtual40=None,grow=None))

    def test_growth_then_link_slot_reload(self):
        c=dict(group408=8,group410=10,groups418=array([]),groups428=array([9]),
               tracked=array([]),pending_links=array([],0))
        g=dict(token=9,index=0,flag_a0=1,count=0,slots=[],link_count=1,link_slots=[20])
        def grow(a,n):a.update(capacity=n,slots=[0]*n);g['link_slots'][0]=21
        finalize_pose_group(c,g,groups={9:g},bodies={1:dict(metadata=dict(kind8=2))},
            links={20:dict(first=1)},virtual40=None,grow=grow)
        self.assertEqual(c['pending_links']['slots'][0],21)
