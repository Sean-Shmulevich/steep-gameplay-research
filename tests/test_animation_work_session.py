import json
import math
from pathlib import Path
import unittest
from engine.animation_work_session import AnimationWorkSession
ROOT=Path(__file__).resolve().parents[1]


class SessionTests(unittest.TestCase):
    def test_connected_receipts_through_session(self):
        for kind in ('work','context'):
            receipt=json.loads((ROOT/f'native/snow_host/{kind}_cycle_validation.json').read_text())
            for sample in receipt['samples']:
                args=sample['inputs'];prior=dict(sample['prior_work'],active_context_token=2)
                seeds=iter(sample['rsqrt_seeds']);calls=iter(sample['math_services'])
                def trig(name,x):
                    row=next(calls);self.assertEqual((name,x),(row['name'],row['input']));return row['output']
                def resolve(token):
                    if kind=='work':return None
                    return dict(basis_rows=args['basis_rows'],position=args['context_position']) if token==2 else sample['replacement_context']
                bank=dict(records=args['records'],parent_position=args['parent_position'],
                    parent_rotation=args['parent_rotation'],direct=args['direct'],flags=args['bank_flags'])
                session=AnimationWorkSession(bank=bank,work=prior,indices=args['indices'],
                    resolve_context=resolve,reciprocal_sqrt=lambda _:next(seeds),
                    acos=lambda x:trig('acos',x),sin=lambda x:trig('sin',x))
                actual=session.advance(args['dt'],bank_present=args['bank_present'])
                expected=json.loads(json.dumps(dict(update=sample['update'],final=sample['final'])))
                expected['final']['work'].setdefault('active_context_token',2)
                self.assertEqual(json.loads(json.dumps(actual)),expected)
                self.assertEqual(list(seeds),[]);self.assertEqual(list(calls),[])

    def test_multiple_requests_and_expiry(self):
        bank=dict(records=[([8.,0.,0.,1.],[0.,0.,0.,1.])],parent_position=None,
                  parent_rotation=None,direct=True,flags=1<<26)
        work=dict(count=0,records=[],elapsed=0.,duration=0.,saved_flag=0,
                  saved_scalar_bits=0,saved_context_token=0,active_context_token=0)
        session=AnimationWorkSession(bank=bank,work=work,indices=[0],resolve_context=lambda _:None,
            reciprocal_sqrt=lambda x:1/math.sqrt(x),acos=math.acos,sin=math.sin)
        self.assertEqual(session.request(1.)['action'],'replaced')
        self.assertEqual(session.request(.75)['action'],'deferred')
        self.assertEqual(session.advance(.25)['final']['action'],'replaced')
        self.assertEqual(session.work['duration'],.75)
        self.assertEqual(session.work['elapsed'],0.)
        self.assertEqual(session.advance(.75)['final']['action'],'no_handoff')
        self.assertEqual(session.work['count'],0)
        self.assertEqual(len(session.work['records']),1)
        snapshot=session.snapshot();snapshot['work']['count']=999
        self.assertEqual(session.work['count'],0)
        self.assertEqual(work['records'],[])

    def test_native_multistep_sequences_with_moving_contexts(self):
        receipt=json.loads((ROOT/'native/snow_host/work_sequence_validation.json').read_text())
        checked=0
        for sample in receipt['samples']:
            args=sample['inputs'];contexts={'2':dict(basis_rows=args['basis_rows'],position=args['context_position']),
                                           '1':sample['replacement_context']}
            seeds=iter(sample['rsqrt_seeds']);calls=iter(sample['math_services'])
            def trig(name,x):
                row=next(calls);self.assertEqual((name,x),(row['name'],row['input']));return row['output']
            session=AnimationWorkSession(bank=dict(records=args['records'],flags=args['bank_flags'],
                direct=args['direct'],parent_position=args['parent_position'],parent_rotation=args['parent_rotation']),
                work=sample['prior_work'],indices=args['indices'],resolve_context=lambda token:contexts[str(token)],
                reciprocal_sqrt=lambda _:next(seeds),acos=lambda x:trig('acos',x),sin=lambda x:trig('sin',x))
            result=session.advance(args['dt'],bank_present=args['bank_present'])
            self.assertEqual(json.loads(json.dumps(result)),dict(update=sample['update'],final=sample['final']))
            self.assertEqual(list(seeds),[]);self.assertEqual(list(calls),[]);checked+=1
            for step in sample['following']:
                contexts=step['contexts'];seeds=iter(step['rsqrt_seeds']);calls=iter(step['math_services'])
                result=session.advance(step['dt'])
                self.assertEqual(json.loads(json.dumps(result)),step['result'])
                self.assertEqual(list(seeds),[]);self.assertEqual(list(calls),[]);checked+=1
        self.assertEqual(checked,receipt['updates'])
