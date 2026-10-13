import unittest
from engine.mixed_scheduler import MixedScheduler


class RangeYieldTests(unittest.TestCase):
    def test_enqueue_during_range_yields_only_after_all_claimed_receivers(self):
        visited=[]
        def receiver(ctx,value):
            visited.append(value)
            if value==3:ctx.submit('urgent')
        m=MixedScheduler([
            dict(id='r',kind='range',receivers=[0,1,2,3],chunk_size=2,handler='visit',successors=['end']),
            dict(id='urgent',kind='callback',front_insert=True),dict(id='end',kind='terminal')],
            {'visit':dict(version='synthetic-v1',callback=receiver)})
        m.submit('r');token=m.reserve();claim=m.claim_range(token)
        m.execute_range(token,claim,m)
        self.assertEqual(visited,[3,2])
        self.assertIsNone(m.claim_range(token))
        m.finish_dispatch(token)
        snapshot=m.snapshot()
        self.assertEqual(snapshot['jobs']['r']['remaining'],2)
        self.assertEqual(snapshot['jobs']['r']['state'],'SCHEDULED')
        self.assertEqual(snapshot['jobs']['end']['terminal_begins'],0)
        self.assertEqual(m.ready()[0],'urgent')
        m.run_ready(context=m)
        self.assertEqual(visited,[3,2,1,0])
        self.assertEqual(m.snapshot()['jobs']['end']['terminal_begins'],1)
        self.assertEqual(m.snapshot()['front_count'],0)

    def test_front_flag_gate_uses_queued_not_running_callback(self):
        for remove_front in (False,True):
            m=MixedScheduler([dict(id='r',kind='range',receivers=[0,1],early_exit_enabled=True),
                              dict(id='front',kind='callback',front_insert=True)])
            m.submit('r');m.submit('front')
            token=m.reserve('r');claim=m.claim_range(token)
            if remove_front:
                front=m.reserve('front')
                self.assertEqual(m.snapshot()['front_count'],0)
                self.assertEqual(m.snapshot()['jobs']['front']['executions'],1)
            m.execute_range(token,claim)
            dispatch=m.snapshot()['dispatches'][str(token.dispatch)]
            self.assertEqual(dispatch['yield_requested'],not remove_front)

    def test_default_flag_ignores_preexisting_front_work(self):
        m=MixedScheduler([dict(id='r',kind='range',receivers=[0,1]),
                          dict(id='front',kind='callback',front_insert=True)])
        m.submit('r');m.submit('front')
        token=m.reserve('r');claim=m.claim_range(token);m.execute_range(token,claim)
        self.assertIsNotNone(m.claim_range(token))

    def test_queue_change_wraps_and_removal_does_not_increment(self):
        m=MixedScheduler([dict(id='c',kind='callback',front_insert=True)])
        m._queue_change=0xffffffff  # Synthetic counter-boundary fixture.
        m.submit('c');self.assertEqual(m.snapshot()['queue_change'],0)
        token=m.reserve();self.assertEqual(m.snapshot()['queue_change'],0)
        self.assertEqual(m.snapshot()['front_count'],0)
        m.execute_callback(token);m.finish_dispatch(token)
