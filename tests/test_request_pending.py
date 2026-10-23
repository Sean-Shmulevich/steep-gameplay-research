import unittest
from engine.request_pending import publish_request,transfer_pending


def ring(items=(), capacity=4):
    return dict(slots=list(items)+[None]*(capacity-len(items)),count=len(items),capacity=capacity,read_index=0,write_index=len(items)%capacity)


class RequestPendingTests(unittest.TestCase):
    def setup_case(self):
        m=dict(pending=[ring() for _ in range(4)],ready=ring(),pending_total=0,normal_outstanding=0,wake_counter=-1)
        events=[]
        s={name:(lambda *args,name=name:events.append(name)) for name in ('lock','unlock','notify','before_transfer','prepare_seed')}
        s['refill']=lambda manager:False
        return m,s,events

    def work(self,mode,**kw):
        return dict(mode=mode,kind=0,reload=False,resource='resource',**kw)

    def test_priority_order_and_wake_coalescing(self):
        m,s,e=self.setup_case()
        for mode in (3,1,0,2):publish_request(m,self.work(mode),services=s)
        self.assertEqual(e.count('notify'),1)
        transfer_pending(m,services=s)
        self.assertEqual([w['mode'] for w in m['ready']['slots']],[0,1,2,3])
        self.assertEqual((m['pending_total'],m['normal_outstanding']),(0,4))

    def test_notification_saturates_old_max_before_increment_wrap(self):
        m,s,e=self.setup_case();m['wake_counter']=0x7fffffff
        publish_request(m,self.work(0),services=s)
        self.assertEqual(m['wake_counter'],1)
        self.assertNotIn('notify',e)
        m['wake_counter']=-0x80000000
        publish_request(m,self.work(0),services=s)
        self.assertEqual(m['wake_counter'],-0x7fffffff)
        self.assertEqual(e.count('notify'),1)

    def test_full_publication_still_accounts(self):
        m,s,e=self.setup_case();m['pending'][0]=ring([self.work(0)],1)
        result=publish_request(m,self.work(0),services=s)
        self.assertFalse(result['inserted'])
        self.assertEqual((m['pending_total'],m['normal_outstanding']),(1,1))

    def test_seed_preparation_stops_even_when_ready_is_full(self):
        m,s,e=self.setup_case();w=self.work(0);w['resource']=None
        m['pending'][0]=ring([w,self.work(0)]);m['pending_total']=2
        m['ready']=ring(['occupied'],1)
        result=transfer_pending(m,services=s)
        self.assertEqual((result['popped'],result['inserted'],result['seed_prepared']),(1,0,True))
        self.assertEqual(m['pending'][0]['count'],1)
        self.assertIn('prepare_seed',e)

    def test_null_pop_does_not_decrement_pending_total(self):
        m,s,e=self.setup_case();m['pending'][0]=ring([None]);m['pending_total']=1
        transfer_pending(m,services=s)
        self.assertEqual(m['pending_total'],1)

    def test_refill_does_not_rescan_earlier_category(self):
        m,s,e=self.setup_case();called=False
        def refill(manager):
            nonlocal called
            if called:return False
            called=True
            manager['pending'][0]=ring([self.work(0)])
            manager['pending'][1]=ring([self.work(1)])
            manager['pending_total']=2
            return True
        s['refill']=refill
        transfer_pending(m,services=s)
        self.assertEqual((m['pending'][0]['count'],m['ready']['count']),(1,1))
        self.assertEqual(m['ready']['slots'][0]['mode'],1)


if __name__ == '__main__':unittest.main()
