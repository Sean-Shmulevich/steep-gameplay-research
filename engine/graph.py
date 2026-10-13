"""Recovered lazy-producer readiness and deferred-evaluation contract.

Callback identity and graph selection are supplied by the caller. This kernel
is independently testable; the default clip runtime does not assume its gate
configuration describes the active original rider graph.
"""
import copy
import math
from .assets import canonical

def read_producer(state,group,field,produce):
    groups=state.setdefault('groups',{})
    cached=groups.setdefault(group,{'ready':False,'values':{}})
    if not cached['ready']:
        values=produce();canonical(values)
        if not isinstance(values,dict):raise ValueError('Producer must return named scalar values')
        cached['values']=copy.deepcopy(values);cached['ready']=True
    if field not in cached['values']:raise KeyError('Missing producer output')
    return copy.deepcopy(cached['values'][field])

def update(state,dt,config,evaluate,cached_callbacks=()):
    if not math.isfinite(dt) or dt<0:raise ValueError('Invalid graph dt')
    threshold=config.get('byte_threshold',1)
    if type(threshold) is not int or not 0<=threshold<=255:raise ValueError('Threshold must be a byte')
    pending=config.get('pending_count',0);flags=config.get('flags',1)
    if not config.get('graph_present',True):return {'path':'no_graph'}
    eligible=bool(cached_callbacks) and pending==0 and flags&5==1
    counter=state.get('byte_counter',0)
    if eligible:
        counter=(counter+1)&255;state['byte_counter']=counter
    if eligible and counter<threshold:
        for callback in cached_callbacks:callback(dt)
        state['accumulated_dt']=state.get('accumulated_dt',0.)+dt
        return {'path':'cached_callbacks','dt':dt}
    effective=state.get('accumulated_dt',0.)+dt
    state['accumulated_dt']=0.;state['byte_counter']=0
    result=evaluate(effective)
    # Readiness reset AFTER full evaluation is a recovered ordering constraint.
    for group in state.get('groups',{}).values():group['ready']=False
    return {'path':'full_evaluation','dt':effective,'result':result}
