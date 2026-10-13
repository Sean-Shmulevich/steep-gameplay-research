import copy
import unittest
from engine.queue_policy import INT_MAX,INT_MIN,occupancy_score,select_queue,select_categories
from engine.mixed_scheduler import MixedScheduler


def job(kind='range',limit=4,executions=0,**kw):
    return dict(kind=kind,limit=limit,executions=executions,**kw)


class QueuePolicyTests(unittest.TestCase):
    def test_signed_wrap_and_truncation(self):
        self.assertEqual(occupancy_score(INT_MAX,3,2),0)
        self.assertEqual(occupancy_score(2**30,1,2),INT_MIN)
        self.assertEqual(occupancy_score(1,0,8),8)
        self.assertEqual(occupancy_score(1,-2,-7),-7)

    def test_scores_strict_ties_and_early_zero(self):
        jobs={'a':job(limit=2,executions=1),'b':job(limit=4,executions=1),'c':job(limit=4,executions=1)}
        result=select_queue(jobs,list(jobs),shared_default=8,worker_mask=0)
        self.assertEqual((result['selected'],result['score']),('b',2))
        jobs={'a':job(),'b':job(limit=INT_MAX)}
        result=select_queue(jobs,list(jobs),shared_default=8,worker_mask=0)
        self.assertEqual(result['visited'],['a']);self.assertEqual(jobs['b']['limit'],INT_MAX)
        self.assertIsNone(select_queue({'a':job('callback',0)},['a'],shared_default=INT_MAX,worker_mask=0)['selected'])

    def test_sentinel_order_and_optional_eligibility(self):
        jobs={'r':job(limit=INT_MAX,required_mask=2),'c':job('callback',INT_MAX,required_mask=2),'o':job(limit=INT_MAX,optional_eligible=False)}
        result=select_queue(jobs,list(jobs),shared_default=8,worker_mask=1)
        self.assertTrue(result['rejected_by_affinity']);self.assertIsNone(result['selected'])
        self.assertEqual([j['limit'] for j in jobs.values()],[8,INT_MAX,INT_MAX])

    def test_required_any_excluded_override_local_bypass(self):
        jobs={'a':job(required_mask=3,excluded_mask=1)}
        self.assertIsNone(select_queue(jobs,['a'],shared_default=8,worker_mask=1)['selected'])
        self.assertEqual(select_queue(jobs,['a'],shared_default=8,worker_mask=2)['selected'],'a')
        self.assertEqual(select_queue(jobs,['a'],shared_default=8,worker_mask=1,local=True)['selected'],'a')

    def test_categories_and_callback_not_capped(self):
        jobs={'l1':job(),'s0':job('callback',1,executions=3),'l0':job(limit=0)}
        result=select_categories(jobs,[['l0'],['l1'],[]],[['s0'],[],[]],shared_default=8,worker_mask=0)
        self.assertEqual(result['selected'],'s0');self.assertEqual(result['source'],'shared')
        self.assertEqual(result['category'],0)

    def test_mixed_selection_reservation_and_readonly_preview(self):
        defs=[{'id':n,'kind':k,**({'receivers':[1,2]} if k=='range' else {})} for n,k in [('range','range'),('callback','callback')]]
        policy=dict(shared_default=2,worker_mask=1,jobs={
            'range':dict(category=1,queue='shared',limit=1),
            'callback':dict(category=0,queue='shared',limit=0)})
        m=MixedScheduler(defs,queue_policy=policy)
        for n in ('range','callback'):m.submit(n)
        before=m.snapshot();self.assertEqual(m.ready(),['callback','range']);self.assertEqual(before,m.snapshot())
        with self.assertRaises(ValueError):m.reserve('range')
        self.assertEqual(before,m.snapshot())
        token=m.reserve();s=m.snapshot()['jobs']['callback']
        self.assertEqual((s['state'],s['executions'],s['outstanding_dispatches']),('DONE',1,1))
        m.execute_callback(token);m.finish_dispatch(token)
        token=m.reserve();self.assertEqual(m.ready(),[])
        self.assertIsNone(m.reserve())
        self.assertEqual(m.snapshot()['jobs']['range']['executions'],1)
        while (r:=m.claim_range(token)) is not None:m.execute_range(token,r)
        m.finish_dispatch(token)
        self.assertEqual(m.snapshot()['jobs']['range']['outstanding_dispatches'],0)

    def test_validation_before_sentinel_mutation(self):
        jobs={'a':job(limit=INT_MAX),'bad':job(executions=True)}
        with self.assertRaises(ValueError):select_queue(jobs,['a'],shared_default=8,worker_mask=0)
        self.assertEqual(jobs['a']['limit'],INT_MAX)
        with self.assertRaises(ValueError):select_categories({'a':job()},[['a'],[],[]],[['a'],[],[]],shared_default=8,worker_mask=0)

    def test_mixed_enqueue_resolves_before_optional_and_affinity_gates(self):
        definitions=[{'id':'r','kind':'range','receivers':[1]}, {'id':'c','kind':'callback'}]
        policy=dict(shared_default=3,worker_mask=1,jobs={
            'r':dict(category=0,queue='shared',limit=INT_MAX,optional_eligible=False),
            'c':dict(category=0,queue='shared',limit=INT_MAX,required_mask=2)})
        m=MixedScheduler(definitions,queue_policy=policy)
        m.submit('r');m.submit('c')
        self.assertEqual([j['limit'] for j in m.snapshot()['selection_jobs'].values()],[3,3])
        self.assertIsNone(m.reserve())
        self.assertEqual(m.snapshot()['jobs']['c']['state'],'SCHEDULED')
