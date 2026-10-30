import unittest
from engine.pose_cleanup_bench import run_pose_cleanup_scenario


class CleanupRuntimeTests(unittest.TestCase):
    def test_joined_lifecycle_and_deferred_queue(self):
        r=run_pose_cleanup_scenario()
        self.assertEqual(r['containers'],[20])
        self.assertEqual(r['individual_constraints'],[30])
        self.assertEqual(r['first_commands'],[30]);self.assertEqual(r['second_commands'],[])
        self.assertEqual(r['queued_constraints'],[80])
        self.assertEqual(r['body_heads'],{'1':30,'2':0,'3':30})
        self.assertEqual((r['tree_active'],r['tree_free']),(0,0))
        self.assertEqual(r['moved_container'],dict(owner=123,index=0,backlink=1008))
        self.assertEqual([(e['operation'],e.get('token')) for e in r['events']],
            [('callback',90),('release_intent',90),('callback',40),('release_intent',40),('grow_output',None)])

    def test_fresh_invocations_do_not_reuse_retired_state(self):
        first=run_pose_cleanup_scenario();first['events'].clear()
        second=run_pose_cleanup_scenario();self.assertEqual(len(second['events']),5)
        self.assertEqual(second['queued_constraints'],[80])


if __name__=='__main__':unittest.main()
