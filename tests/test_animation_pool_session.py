import json
from pathlib import Path
import unittest
from engine.animation_pool_session import AnimationPoolSession,run


class PoolSessionTests(unittest.TestCase):
    def example(self):
        return json.loads((Path(__file__).resolve().parents[1]/'engine/examples/animation_pool_input.json').read_text())

    def test_sequence_releases_before_reuse_and_reports_missing_allocation(self):
        doc=self.example();result=run(doc);ops=result['operations']
        self.assertEqual([x['result']['status'] for x in ops[:2]],['reused','allocation_required'])
        self.assertEqual(ops[0]['state'],ops[1]['state'])
        self.assertTrue(ops[2]['result']['matched'])
        self.assertEqual(ops[3]['services'][0]['service'],'copy_selected')
        self.assertFalse(ops[3]['services'][0]['executed'])
        self.assertEqual(ops[4]['state']['entries'][0]['occupied_mask'],0)
        self.assertEqual(ops[4]['services'],[])
        self.assertEqual(ops[4]['result'][0]['flags'],4)
        self.assertEqual(doc,self.example())
        self.assertEqual(result,run(doc))

    def test_services_receive_actual_shared_bank_and_mutations_persist(self):
        banks={'a':dict(flags=0,auxiliary_mask=1,auxiliary_count=1)}
        entries=[dict(bank='a',occupied_mask=0,initialized_mask=1,representation_word=0)]
        events=[]
        def copy(dst,src,mode,mask):dst['copied']=src;events.append('copy')
        def clear(bank):bank['cleared']=True;events.append('clear')
        session=AnimationPoolSession(banks,entries,copy_selected=copy,clear_auxiliary=clear,free_storage=lambda s:events.append(s))
        session.acquire(1,0,0,'synthetic')
        session.release('a',1)
        self.assertEqual(events,['copy','clear'])
        state=session.snapshot();self.assertEqual(state['banks']['a']['copied'],'synthetic')
        self.assertTrue(state['banks']['a']['cleared'])
        self.assertEqual(state['banks']['a']['auxiliary_count'],0)
        state['banks']['a']['flags']=0
        self.assertNotEqual(session.snapshot()['banks']['a']['flags'],0)
        self.assertNotIn('copied',banks['a'])

    def test_cleanup_requires_identity_not_equal_bank_contents(self):
        base=dict(flags=1<<26,auxiliary_mask=0,auxiliary_count=0)
        session=AnimationPoolSession({'a':base,'b':base},[
            dict(bank=n,occupied_mask=1,initialized_mask=1,representation_word=0) for n in ('a','b')],
            copy_selected=lambda *a:None,clear_auxiliary=lambda *a:None,free_storage=lambda *a:None)
        def wrapper(name):return dict(primary=name,alternate=None,flags=4,index=1,header=32772,storage=None)
        session.cleanup(wrapper('b'),wrapper(None))
        self.assertEqual([e['occupied_mask'] for e in session.snapshot()['entries']],[1,0])

    def test_explicit_service_policy_required(self):
        doc=self.example();doc.pop('service_policy')
        with self.assertRaises(ValueError):run(doc)

    def test_invalid_mask_and_unknown_operation_refused(self):
        doc=self.example();doc['operations'][0]['request_mask']=65536
        with self.assertRaises(ValueError):run(doc)
        doc=self.example();doc['operations'][0]['op']='allocate'
        with self.assertRaises(ValueError):run(doc)

    def test_explicit_copy_policy_executes_partial_and_full_paths(self):
        doc=json.loads((Path(__file__).resolve().parents[1]/'engine/examples/animation_pool_copy_input.json').read_text())
        result=run(doc);ops=result['operations']
        self.assertEqual(ops[0]['state']['banks']['pose_a']['data'][:12],list(range(12)))
        self.assertEqual(ops[0]['state']['banks']['pose_a']['data'][12:],[194]*84)
        self.assertTrue(ops[0]['services'][0]['executed'])
        self.assertEqual(ops[-1]['services'][0]['result']['path'],'full')
        self.assertEqual(ops[-1]['state']['banks']['pose_a']['data'][:85],list(range(85)))
        self.assertEqual(ops[-1]['state']['banks']['pose_a']['data'][85:],[194]*11)
        self.assertEqual(ops[-1]['state']['banks']['pose_a']['parent_header'],[0]*32)
        self.assertEqual(ops[-1]['state']['banks']['pose_a']['flags'] & (1<<27),0)
        json.dumps(result,allow_nan=False)
        self.assertEqual(doc['banks']['pose_a']['data'],[194]*96)
