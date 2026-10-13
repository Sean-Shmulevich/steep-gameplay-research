import unittest
from engine.mixed_scheduler import MixedScheduler


class HelperDispatchTests(unittest.TestCase):
    def model(self):
        return MixedScheduler([dict(id='r',kind='range',receivers=[0,1],successors=['end']),
            dict(id='end',kind='terminal')], queue_policy=dict(shared_default=1,
            worker_slots=[True], jobs={'r':dict(category=0,limit=1)}))

    def test_helper_bypasses_cap_and_waits_for_other_return(self):
        m=self.model();m.submit('r')
        worker=m.reserve(worker_index=0);held=m.claim_range(worker)
        helper=m.reserve_helper('r',helper_id='helping-thread')
        self.assertEqual(m.snapshot()['jobs']['r']['executions'],2)
        claimed=m.claim_range(helper);m.execute_range(helper,claimed);m.finish_dispatch(helper)
        before=m.snapshot();status=m.helper_wait_status('r')
        self.assertEqual(before,m.snapshot())
        self.assertTrue(status['empty']);self.assertFalse(status['wait_complete'])
        self.assertEqual(m.snapshot()['jobs']['end']['terminal_begins'],0)
        self.assertIsNone(m.reserve_helper('r',helper_id='helping-thread'))
        m.execute_range(worker,held);m.finish_dispatch(worker)
        self.assertTrue(m.helper_wait_status('r')['wait_complete'])
        self.assertEqual(m.snapshot()['jobs']['end']['terminal_begins'],1)

    def test_helper_does_not_select_by_affinity(self):
        m=MixedScheduler([dict(id='r',kind='range',receivers=[0])],queue_policy=dict(
            shared_default=1,worker_slots=[True],jobs={'r':dict(category=0,limit=0,excluded_mask=1)}))
        m.submit('r');self.assertIsNone(m.reserve(worker_index=0))
        token=m.reserve_helper('r',helper_id='explicit')
        claim=m.claim_range(token);m.execute_range(token,claim);m.finish_dispatch(token)
        self.assertTrue(m.helper_wait_status('r')['wait_complete'])

    def test_invalid_helper_scope_does_not_mutate(self):
        m=self.model();before=m.snapshot()
        with self.assertRaises(ValueError):m.reserve_helper('r',helper_id='inactive')
        with self.assertRaises(ValueError):m.reserve_helper('end',helper_id='wrong-kind')
        self.assertEqual(before,m.snapshot())
        m.submit('r');m.reserve_helper('r',helper_id='busy');before=m.snapshot()
        with self.assertRaises(ValueError):m.reserve_helper('r',helper_id='busy')
        self.assertEqual(before,m.snapshot())
