"""Explicit-call animation work runner; no inferred scheduler or native ownership.

Evidence: docs/reconstruction/ANIMATION_WORKBENCH.md, Stateful work sessions.
Numerical services and context resolution are supplied by the caller.
"""
from copy import deepcopy
from reference.snow import f32
from reference.animation_evaluator import evaluate_work_request, finish_work_update
from reference.animation_work_application import update_context_free_work, update_context_work


class AnimationWorkSession:
    def __init__(self, *, bank, work, indices, resolve_context, reciprocal_sqrt, acos, sin):
        if type(bank['direct']) is not bool or bool(bank['flags'] & (1<<26))!=bank['direct']:
            raise ValueError('bank mode and flag bit 26 must agree')
        if type(work['count']) is not int or not 0<=work['count']<=len(work['records']):
            raise ValueError('active work count outside backing records')
        if 'active_context_token' not in work:
            raise ValueError('explicit active context token required')
        self.bank=deepcopy(bank);self.work=deepcopy(work);self.indices=list(indices)
        self.work['elapsed']=f32(self.work['elapsed'])
        self.work['duration']=f32(self.work['duration'])
        self.resolve_context=resolve_context
        self.services=dict(reciprocal_sqrt=reciprocal_sqrt,acos=acos,sin=sin)

    def snapshot(self):
        return deepcopy(dict(bank=self.bank,work=self.work,indices=self.indices))

    def request(self, duration, context_token=0):
        result=evaluate_work_request(self.work,duration,context_token,
            self.bank['records'],self.indices,self.bank['parent_position'],
            self.bank['parent_rotation'],self.bank['direct'],self.resolve_context,
            self.services['reciprocal_sqrt'])
        self.work=result['work']
        return deepcopy(result)

    def advance(self, dt, *, bank_present=True):
        # Count controls active records; unused backing storage is not pose work.
        args=dict(records=self.bank['records'],indices=self.indices,
            saved=self.work['records'][:self.work['count']],
            parent_position=self.bank['parent_position'],parent_rotation=self.bank['parent_rotation'],
            direct=self.bank['direct'],elapsed=self.work['elapsed'],duration=self.work['duration'],
            dt=dt,bank_flags=self.bank['flags'],saved_flag=self.work['saved_flag'],
            bank_present=bank_present,**self.services)
        # Resolve lazily: native expiry and missing-bank paths never touch context.
        from reference.animation_work_timing import advance_work_clock
        clock=advance_work_clock(args['elapsed'],args['duration'],dt,self.work['count'],bank_present)
        context=self.resolve_context(self.work['active_context_token']) if clock['action']=='apply' else None
        if context is None:
            update=update_context_free_work(**args)
        else:
            update=update_context_work(**args,basis_rows=context['basis_rows'],context_position=context['position'])
        final=finish_work_update(update,self.work,self.indices,self.bank['parent_position'],
            self.bank['parent_rotation'],self.bank['direct'],self.resolve_context,
            self.services['reciprocal_sqrt'])
        self.bank['records']=update['records'];self.bank['flags']=update['bank_flags']
        self.work=final['work']
        return deepcopy(dict(update=update,final=final))
