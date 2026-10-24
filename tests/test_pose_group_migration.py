import unittest
from engine.pose_group_migration import migrate_pose_group


def group(token,body_slots):
    return dict(token=token,count=len(body_slots),capacity=8,slots=body_slots+[0]*8,
                link_count=0,link_capacity=8,link_slots=[0]*8,
                pose_count=0,pose_capacity=8,pose_slots=[0]*8)


class MigrationTests(unittest.TestCase):
    def test_move_reprocesses_swapped_body_and_constraints_follow_first(self):
        s=group(9,[1,2,3]);t=group(10,[])
        s.update(link_count=1,link_slots=[20]*8,pose_count=1,pose_slots=[30]*8)
        bodies={i:dict(group=9,index=i-1) for i in (1,2,3)}
        links={20:dict(first=1,second=2,index=0)}
        poses={30:dict(first=3,second=2,index=0,group=9)}
        d=dict(count=3,slots=[10,9,10])
        migrate_pose_group(s,d,groups={9:s,10:t},bodies=bodies,links=links,poses=poses,grow=None)
        self.assertEqual(s['slots'][0],2);self.assertEqual(s['count'],1)
        self.assertEqual(t['slots'][:2],[1,3]);self.assertEqual(d['count'],1)
        self.assertEqual((t['link_count'],t['pose_count']),(1,1))
        self.assertEqual(poses[30]['group'],10)

    def test_full_pose_destination_leaves_record_detached(self):
        s=group(9,[1]);t=group(10,[]);t['pose_count']=65535
        s.update(pose_count=1,pose_slots=[30]*8)
        bodies={1:dict(group=9,index=0)};poses={30:dict(first=1,index=0,group=9)}
        migrate_pose_group(s,dict(count=1,slots=[10]),groups={9:s,10:t},bodies=bodies,
                           links={},poses=poses,grow=None)
        self.assertEqual(poses[30],dict(first=1,index=0xffffffff,group=0))
        self.assertEqual(s['pose_count'],0);self.assertEqual(t['pose_count'],65535)
