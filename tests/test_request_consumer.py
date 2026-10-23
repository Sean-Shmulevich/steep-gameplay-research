import unittest
from engine.request_consumer import consume_requests


class RequestConsumerTests(unittest.TestCase):
    def case(self, **changes):
        events=[];manager=dict(stop=False,active=None)
        work=dict(kind=0,descriptor=None,resource='resource',seed=None,payload='payload',mode=1,associated='associated',reload=False,context='context')
        work['callback']=lambda code,associated,w,context:events.append(('callback',code,manager['active'] is w))
        work.update(changes)
        def acquire(m):m['active']=work
        def recycle(m,w):events.append(('recycle',m['active'],w is work))
        def signal():events.append('signal');manager['stop']=True
        services={name:(lambda *args,name=name:events.append(name)) for name in ('reset_event','prepare','defer','release_seed','alternate','lock','unlock')}
        services.update(acquire_active=acquire,recycle=recycle,signal=signal,descriptor_ready=lambda d:True,materialize=lambda w,flag:w.update(resource='created'))
        return manager,work,events,services

    def test_three_codes_and_clear_before_recycle(self):
        for changes,code in [({},0),({'resource':None},1),({'reload':True},2)]:
            m,w,e,s=self.case(**changes)
            result=consume_requests(m,services=s)
            self.assertEqual(e[-5:],[('callback',code,True),'lock',('recycle',None,True),'unlock','signal'])
            self.assertEqual(result['callbacks'],1)

    def test_failed_materialization_and_absent_callback_skip_delivery(self):
        for changes in ({'resource':None},{'callback':None}):
            m,w,e,s=self.case(**changes);s['materialize']=lambda w,flag:None
            self.assertEqual(consume_requests(m,services=s)['callbacks'],0)
            self.assertIn(('recycle',None,True),e)

    def test_descriptor_refusal_and_alternate(self):
        for changes,expected in [({'descriptor':'x'},'defer'),({'kind':1},'alternate')]:
            m,w,e,s=self.case(**changes);s['descriptor_ready']=lambda d:False
            self.assertEqual(consume_requests(m,services=s)['callbacks'],0)
            self.assertIn(expected,e)

    def test_no_active_signals_but_entry_stop_only_resets(self):
        m,w,e,s=self.case();s['acquire_active']=lambda m:None
        consume_requests(m,services=s)
        self.assertEqual(e,['reset_event','prepare','signal'])
        m,w,e,s=self.case();m['stop']=True
        consume_requests(m,services=s)
        self.assertEqual(e,['reset_event'])

    def test_composed_cleanup_precedes_recycle_but_skip_does_not_free(self):
        from engine.examples.request_lifecycle_probe import run_case
        success=run_case(True);failure=run_case(False)
        self.assertLess(success['events'].index('free_context'),success['events'].index(['recycle',True]))
        self.assertFalse(failure['context_free_observed'])
        self.assertEqual(failure['callback_count'],0)
        self.assertIn(['recycle',True],failure['events'])

    def test_exception_does_not_invent_retirement(self):
        def fail(*args):raise RuntimeError('callback failed')
        m,w,e,s=self.case(callback=fail)
        with self.assertRaises(RuntimeError):consume_requests(m,services=s)
        self.assertIs(m['active'],w)
        self.assertNotIn('lock',e)


if __name__ == '__main__':unittest.main()
