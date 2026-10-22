import json
from pathlib import Path
import unittest
from reference.skeleton_refresh import plan_guarded_refresh


class SkeletonRefreshTests(unittest.TestCase):
    def test_original_instruction_branches(self):
        path = Path(__file__).resolve().parents[1] / 'native/snow_host/guarded_refresh_validation.json'
        receipt = json.loads(path.read_text())
        self.assertEqual(receipt['cases'], 512)
        for row in receipt['rows']:
            with self.subTest(inputs=row['inputs']):
                result = plan_guarded_refresh(**row['inputs'])
                self.assertEqual(result['events'], row['events'])
                self.assertEqual(result['dirty_after'], row['dirty_after'])

    def test_post_lock_clean_state_skips_transform_work(self):
        r = plan_guarded_refresh(128, True, 1, 7, True, 0)
        self.assertEqual([e['service'] for e in r['events']], ['lock','evaluate','unlock'])
        self.assertEqual(r['events'][1]['dirty_seen'], 7)

    def test_dirty_clear_precedes_evaluation(self):
        r = plan_guarded_refresh(255, True, 1, 255, False, 0)
        self.assertEqual(r['events'][-2]['dirty_seen'], 127)
        self.assertEqual(r['dirty_after'],127)

    def test_propagation_original_tail(self):
        from reference.skeleton_refresh import plan_pose_propagation
        path = Path(__file__).resolve().parents[1] / 'native/snow_host/pose_propagation_validation.json'
        receipt = json.loads(path.read_text())
        self.assertEqual(receipt['cases'],64)
        for row in receipt['rows']:
            with self.subTest(inputs=row['inputs']):
                actual=plan_pose_propagation(**row['inputs'])
                for key in ('events','dirty_after','pending_after'):
                    self.assertEqual(actual[key],row[key])

    def test_callback_enables_event_and_zero_secondary_defers_child(self):
        from reference.skeleton_refresh import plan_pose_propagation
        r=plan_pose_propagation(False,True,True,0,2,4)
        self.assertEqual(r['events'],['transform_callback','transform_event','find_skeleton'])
        self.assertEqual((r['dirty_after'],r['pending_after']),(130,5))

    def test_post_list_native_selection(self):
        from reference.skeleton_refresh import plan_skeleton_post_list
        p=Path(__file__).resolve().parents[1]/'native/snow_host/skeleton_post_route_validation.json'
        receipt=json.loads(p.read_text())
        self.assertEqual(receipt['setup_sites'],3)
        for row in receipt['rows']:
            entities=[(bool(row['world_mask']&(1<<i)),bool(row['skeleton_mask']&(1<<i))) for i in range(3)]
            self.assertEqual(plan_skeleton_post_list(entities),row['events'])

    def test_post_list_empty_and_missing_world(self):
        from reference.skeleton_refresh import plan_skeleton_post_list
        self.assertEqual(plan_skeleton_post_list([]),[])
        self.assertEqual(plan_skeleton_post_list([(False,True),(True,False)]),[['lookup',1]])
