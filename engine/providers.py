"""Portable resource-handle boundary with explicit synthetic provider identities.

Evidence: docs/reconstruction/research/animation.md, 'Portable pseudocode'.
Keys copy unchanged; equal provider identity preserves backing even on key change.
Lookup writes scalar/flag before availability and continues after unavailable rows.
Python identities, callback interfaces and allocation failures model the boundary;
this is not an original-process resource manager or authored UID conversion.
"""
import copy


def initialize(handle, key, provider_callback, *, override=None, allocate=None):
    """Mutate handle in recovered order; return diagnostic lifecycle events.

    Providers use caller-owned identity objects, compared with `is`. key is an
    opaque immutable scalar. allocate(provider) returns backing or None. Reset
    is represented as dropping existing backing, not native destructor behavior.
    """
    if not isinstance(key,(str,int)) or isinstance(key,bool):
        raise ValueError('Resource key must be an opaque integer or string')
    handle['key']=key
    provider=provider_callback(key) if override is None else override
    old=handle.get('backing')
    if old is not None and old['provider'] is provider:
        return ['key_written','backing_retained']
    events=['key_written','backing_reset']
    handle['backing']=None
    factory=allocate or (lambda p: {'provider':p,'counter':1,'extra':None})
    handle['backing']=factory(provider)
    events.append('allocation_failed' if handle['backing'] is None else 'backing_created')
    return events


def resolve(rows,key,outputs):
    """Return available equal-key resource; preserve outputs from failed matches."""
    for row in rows:
        if row['key']!=key:continue
        outputs['scalar']=copy.deepcopy(row['scalar'])
        outputs['flag']=copy.deepcopy(row['flag'])
        if row['available']:
            return row['resource']
    return None
