import unittest
from engine.pose_group_cleanup import cleanup_pose_group


class CleanupTests(unittest.TestCase):
    def fixture(self):
        return dict(table=99,
                    poses=dict(pointer=30,count=2,capacity=8),
                    links=dict(pointer=20,inline=21,count=3,capacity=8),
                    bodies=dict(pointer=10,inline=11,count=1,capacity=4))

    def test_release_order_and_final_state(self):
        g=self.fixture();calls=[]
        cleanup_pose_group(g,group_table=1,base_table=2,
                           release=calls.append,allocate_zero=lambda *a:0)
        self.assertEqual(calls,[30,20,10]);self.assertEqual(g['table'],2)
        for family in ('poses','links','bodies'):
            self.assertEqual([g[family][k] for k in ('pointer','count','capacity')],[0,0,0])

    def test_inline_arrays_not_released(self):
        g=self.fixture();calls=[]
        for family in ('links','bodies'):g[family]['pointer']=g[family]['inline']
        cleanup_pose_group(g,group_table=1,base_table=2,
                           release=calls.append,allocate_zero=lambda *a:0)
        self.assertEqual(calls,[30])

    def test_zero_capacity_preserves_counts_and_pose_pointer(self):
        g=self.fixture()
        for family in ('poses','links','bodies'):g[family]['capacity']=0
        cleanup_pose_group(g,group_table=1,base_table=2,
                           release=lambda p:self.fail('release'),
                           allocate_zero=lambda *a:self.fail('allocate'))
        self.assertEqual(g['poses']['pointer'],30)
        self.assertEqual([g[f]['count'] for f in ('poses','links','bodies')],[2,3,1])
        self.assertEqual(g['links']['pointer'],0)

    def test_null_pose_branch_and_callback_reload(self):
        g=self.fixture();g['poses']['pointer']=0;calls=[]
        def allocate(*args):calls.append(args);return 40
        def release(p):
            calls.append(p)
            if p==20:g['bodies']['pointer']=11
        cleanup_pose_group(g,group_table=1,base_table=2,release=release,allocate_zero=allocate)
        self.assertEqual(calls,[(0,16,55),20])
        self.assertEqual(g['poses']['pointer'],40)
