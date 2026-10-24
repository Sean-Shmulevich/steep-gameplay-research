import unittest
from engine.pose_group_process import process_pose_group


class GroupProcessTests(unittest.TestCase):
    def run_case(self, count, *, flags=8, eligible_result=1, components=0,
                 seeds=None, finalize_count=None, fail_migration=False):
        self.events=[]
        context={'group410':10}
        group={'token':9,'count':count,'slots':list(range(count))}
        bodies={i:{'metadata':{'flags8':flags}} for i in range(count)}
        def finalize(c,g):
            self.events.append('finalize')
            if finalize_count is not None:g['count']=finalize_count
        def eligible(c,b):
            self.events.append('eligible');c['group410']=11
            return eligible_result
        def remove(g,b):
            self.events.append('remove_body');context['group410']=12
        def append(t,b):
            self.events.append(('append',t));return False
        def allocate(n):
            self.events.append(('allocate',n));return [None]*(n//8)
        def prepare(c,g,d):
            self.events.append('prepare')
            d['slots'][:]=seeds or [0]*count
            d['count']=123  # Native caller reconstructs this before migration.
            return components
        def migrate(g,d):
            self.events.append(('migrate',d['count'],d['slots'][:]))
            if fail_migration:raise RuntimeError('supplied failure')
            g['count']=0;d['count']=0
        return process_pose_group(
            context,group,bodies=bodies,finalize=finalize,eligible=eligible,
            remove_body=remove,append_body=append,allocate=allocate,
            prepare=prepare,acquire_group=lambda c:20,migrate=migrate,
            release=lambda s:self.events.append('release'),
            remove_group=lambda c,g:self.events.append('remove_group'),
            destroy=lambda g,a:self.events.append(('destroy',a)))

    def test_count_is_read_after_finalization(self):
        self.assertTrue(self.run_case(2,finalize_count=0))
        self.assertEqual(self.events,['finalize','remove_group',('destroy',1)])

    def test_single_body_ignores_append_failure_and_reloads_destination(self):
        self.assertTrue(self.run_case(1))
        self.assertEqual(self.events,['finalize','eligible','remove_body',
                                     ('append',12),'remove_group',('destroy',1)])

    def test_single_body_metadata_and_low_byte_gates(self):
        self.assertFalse(self.run_case(1,flags=0))
        self.assertEqual(self.events,['finalize'])
        self.assertFalse(self.run_case(1,eligible_result=256))
        self.assertEqual(self.events,['finalize','eligible'])

    def test_all_eligible_releases_storage_before_retirement(self):
        self.assertTrue(self.run_case(2))
        self.assertIn(('migrate',2,[11,11]),self.events)
        self.assertEqual(self.events[-3:],['release','remove_group',('destroy',1)])

    def test_retirement_uses_selection_not_post_migration_count(self):
        self.assertFalse(self.run_case(2,flags=0))
        self.assertIn(('migrate',2,[9,20]),self.events)
        self.assertEqual(self.events[-1],'release')
        self.assertFalse(self.run_case(2,components=1,seeds=[9,9]))
        self.assertNotIn('eligible',self.events)

    def test_callback_failure_has_no_invented_cleanup(self):
        with self.assertRaises(RuntimeError):self.run_case(2,fail_migration=True)
        self.assertNotIn('release',self.events)
        self.assertNotIn('remove_group',self.events)
