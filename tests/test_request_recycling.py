import unittest
from engine.request_recycling import reset_request,recycle_request


class RequestRecyclingTests(unittest.TestCase):
    def case(self):
        work=dict(payload='payload',resource_holder='r',descriptor_holder='d',callback='callback',alternate='alternate',context='context',associated='associated',marked=True,reload=True,tracked=False,kind=0,mode=3,seed='seed')
        holders={'r':dict(status=1),'d':dict(status=2),'default':dict(status=100)}
        events=[]
        services={name:(lambda *args,name=name:events.append(name)) for name in ('release_holder','allocation_token','destroy_seed','free_seed','unlink_tracking','lock','unlock')}
        services['clear_associated']=lambda w:events.append('clear_associated') or w.update(associated=None)
        return work,holders,events,services

    def test_reset_clears_context_without_callback_or_context_free(self):
        w,h,e,s=self.case()
        reset_request(w,h,default_holder='default',services=s)
        self.assertEqual(e,['release_holder','clear_associated','allocation_token','destroy_seed','free_seed'])
        self.assertIsNone(w['context']);self.assertIsNone(w['callback'])
        self.assertEqual((w['kind'],w['mode'],h['r']['status'],h['d']['status']),(1,1,0,1))
        self.assertFalse(w['tracked']);self.assertIsNone(w['seed'])

    def test_pool_full_still_increments_and_uses_pre_reset_kind(self):
        w,h,e,s=self.case()
        pool=dict(slots=['occupied'],count=1,capacity=1,write_index=0,available_total=1,normal_outstanding=1)
        result=recycle_request(pool,w,reset=lambda w:reset_request(w,h,default_holder='default',services=s),services=s)
        self.assertFalse(result['inserted'])
        self.assertEqual((pool['count'],pool['available_total'],pool['normal_outstanding']),(1,2,0))
        self.assertEqual(pool['slots'],['occupied'])

    def test_success_returns_same_object_and_wraps(self):
        w,h,e,s=self.case();w['kind']=7;w['tracked']=True
        pool=dict(slots=[None,None],count=0,capacity=2,write_index=1,available_total=0xffffffff,normal_outstanding=3)
        recycle_request(pool,w,reset=lambda w:reset_request(w,h,default_holder='default',services=s),services=s)
        self.assertIs(pool['slots'][1],w)
        self.assertEqual((pool['write_index'],pool['available_total'],pool['normal_outstanding']),(0,0,3))
        self.assertEqual(e[0],'unlink_tracking')

    def test_reset_alias_releases_only_after_second_decrement(self):
        w,h,e,s=self.case();w['resource_holder']='d';w['seed']=None
        reset_request(w,h,default_holder='default',services=s)
        self.assertEqual(e,['release_holder','clear_associated'])
        self.assertEqual(h['d']['status'],0)


if __name__ == '__main__':unittest.main()
