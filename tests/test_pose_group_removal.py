import unittest
from engine.pose_group_removal import remove_pose_group


class GroupRemovalTests(unittest.TestCase):
    def test_flag_selects_array_and_removed_group_keeps_index(self):
        for flag in (0,1,255):
            group=dict(token=9,index=0,flag_a0=flag)
            c=dict(groups418=dict(count=2,slots=[9,10]),groups428=dict(count=2,slots=[9,11]))
            groups={9:group,10:dict(index=1),11:dict(index=1)}
            key='groups428' if flag else 'groups418';moved=c[key]['slots'][1]
            remove_pose_group(c,group,groups=groups)
            self.assertEqual(c[key],dict(count=1,slots=[moved,moved]))
            self.assertEqual(groups[moved]['index'],0)
            self.assertEqual(group,dict(token=9,index=0,flag_a0=flag))
            with self.assertRaises(ValueError):remove_pose_group(c,group,groups=groups)
