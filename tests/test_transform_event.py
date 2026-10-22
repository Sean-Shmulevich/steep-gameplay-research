import json
from pathlib import Path
import unittest
from reference.transform_event import plan_transform_event


class TransformEventTests(unittest.TestCase):
    def test_original_routes_and_lock_depth(self):
        p=Path(__file__).resolve().parents[1]/'native/snow_host/transform_event_validation.json'
        receipt=json.loads(p.read_text())
        self.assertEqual(receipt['cases'],27)
        for row in receipt['rows']:
            r=plan_transform_event(row['variant'],row['initial_depth'],row['component_count'])
            expected=[dict(service=e['service'],lock_depth=e['lock'][2],
                           **({'component':e['component']} if 'component' in e else {})) for e in row['events']]
            self.assertEqual(r['events'],expected)
            self.assertEqual(r['final_depth'],row['final_lock'][2])
            self.assertEqual(r['lock_released'],row['final_lock'][0]==0)

    def test_derived_tail_can_still_be_under_outer_lock(self):
        r=plan_transform_event('derived_a',3,0)
        self.assertEqual(r['events'][-1],dict(service='derived_propagation',lock_depth=3))
        self.assertFalse(r['lock_released'])
        self.assertFalse(r['callback_completion_established'])

    def test_skeleton_invalidation_exhaustive_native_digest(self):
        import hashlib
        from reference.transform_event import skeleton_after_transform
        p=Path(__file__).resolve().parents[1]/'native/snow_host/skeleton_transform_notice_validation.json'
        receipt=json.loads(p.read_text())
        self.assertEqual(receipt['cases'],65536)
        unchanged=hashlib.sha256();changed=hashlib.sha256()
        for dirty in range(256):
            for pending in range(256):
                unchanged.update(bytes([dirty,pending]))
                r=skeleton_after_transform(dirty,pending)
                changed.update(bytes([r['dirty'],r['pending']]))
        self.assertEqual(unchanged.hexdigest(),receipt['before_sha256'])
        self.assertEqual(changed.hexdigest(),receipt['after_sha256'])

    def test_invalidation_prevents_treating_event_return_as_ready(self):
        from reference.transform_event import skeleton_after_transform
        from reference.skeleton_refresh import plan_guarded_refresh
        state=skeleton_after_transform(0,0)
        self.assertEqual(state,dict(dirty=128,pending=1))
        refresh=plan_guarded_refresh(state['dirty'],False,state['pending'],
                                     state['dirty'],False,0)
        self.assertEqual(refresh['dirty_after'],0)
        self.assertNotIn('evaluate',[x['service'] for x in refresh['events']])
