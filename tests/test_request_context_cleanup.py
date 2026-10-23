import unittest
from engine.request_context_cleanup import complete_request_context


class RequestContextCleanupTests(unittest.TestCase):
    def case(self, flags, strong_status=1, weak_count=1, weak_status=0):
        context=dict(value=7,weak_holder='w',strong_holder='s',parameter=9,flags=flags)
        target={};holders={'s':dict(status=strong_status,weak=0),'w':dict(status=weak_status,weak=weak_count)}
        seen=[]
        services={name:(lambda *args,name=name:seen.append(name)) for name in ('activate','refresh','apply_holder','optional0','optional1','optional2','allocation_token','release_strong','release_weak','free_context')}
        return context,target,holders,seen,services

    def test_order_flags_and_release_before_free(self):
        c,t,h,seen,s=self.case([1,2,255])
        complete_request_context(c,t,h,services=s)
        self.assertEqual(seen,['activate','refresh','apply_holder','optional0','optional1','optional2','allocation_token','release_strong','release_weak','free_context'])
        self.assertEqual((t['value'],h['s']['status'],h['w']['weak']),(7,0,0))

    def test_nonfinal_references_do_not_release(self):
        c,t,h,seen,s=self.case([0,0,0],strong_status=2,weak_count=1,weak_status=1)
        complete_request_context(c,t,h,services=s)
        self.assertEqual(seen,['activate','refresh','apply_holder','allocation_token','free_context'])

    def test_alias_uses_updated_strong_status(self):
        c,t,h,seen,s=self.case([0,0,0])
        c['weak_holder']='s';h['s']['weak']=1
        complete_request_context(c,t,h,services=s)
        self.assertEqual(seen[-3:],['release_strong','release_weak','free_context'])

    def test_callback_exception_does_not_invent_cleanup(self):
        c,t,h,seen,s=self.case([0,0,0])
        def fail(target):raise RuntimeError('opaque refresh failed')
        s['refresh']=fail
        with self.assertRaises(RuntimeError):complete_request_context(c,t,h,services=s)
        self.assertEqual(seen,['activate'])
        self.assertEqual(h['s']['status'],1)


if __name__ == '__main__':unittest.main()
