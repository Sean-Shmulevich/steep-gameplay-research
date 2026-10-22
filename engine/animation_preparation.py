"""Recovered preparation flow over independent bank/work storage.

Lock/unlock events describe native order; they do not acquire native locks.
Evidence: CENTRAL_IMPULSE.md, Integrated skeleton preparation.
"""
from copy import deepcopy
from reference.snow import f32
from reference.animation_hierarchy import compose_primary_hierarchy, reconcile_current_hierarchy
from engine.animation_work_session import AnimationWorkSession


def prepare_animation(current, primary, work, indices, metadata, use_primary,
                      scalar, context_token, component_flags, pending, dt,
                      resolve_context, reciprocal_sqrt, acos, sin, hierarchy_prefix_count=None):
    current,primary=deepcopy(current),deepcopy(primary)
    selected=primary if use_primary else current
    session=AnimationWorkSession(bank=selected,work=work,indices=indices,
        resolve_context=resolve_context,reciprocal_sqrt=reciprocal_sqrt,acos=acos,sin=sin)
    events=[];scalar=f32(scalar);evaluation=None;update=None;processing=None
    if scalar>=0:
        events.append('evaluate');evaluation=session.request(scalar,context_token);scalar=-1.
    mask=(component_flags>>3)&7
    if session.work['count']:
        if not mask:
            events.append('clear_work');session.work.update(count=0,elapsed=0.,duration=0.)
        else:
            events.extend(['lock','apply']);update=session.advance(dt)
            if use_primary:primary=session.bank
            else:current=session.bank
            events.append('process_primary' if use_primary else 'process_current')
            if use_primary:
                processing=compose_primary_hierarchy(current['records'],primary['records'],metadata,mask,reciprocal_sqrt)
                current['records']=processing['records']
                current['flags'] &= ~(1<<27);primary['flags'] &= ~(1<<27)
            elif metadata:
                processing=reconcile_current_hierarchy(current['records'],primary['records'],metadata,mask,reciprocal_sqrt,processed_count=hierarchy_prefix_count)
                current['records']=processing['current'];primary['records']=processing['primary']
                current['flags'] &= ~(1<<27);primary['flags'] &= ~(1<<27)
            pending |= 1;events.append('unlock')
    return dict(current=current,primary=primary,work=deepcopy(session.work),scalar=scalar,
        pending=pending,mask=mask,events=events,evaluation=evaluation,update=update,processing=processing)
