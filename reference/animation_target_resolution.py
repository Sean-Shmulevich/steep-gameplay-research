"""Recovered ordered target lookup; no lifetime acquisition is implied."""


def resolve_target(*, key_present, enabled, primary_entry_present,
                   primary_value, secondary_value, fallback_value):
    """Service values are supplied symbolic identities; None denotes null.

    A present primary entry returns its payload even when null. Only a missing
    primary entry tries the secondary service, then the paired-map fallback.
    Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Paired-map resolution fallback.
    """
    if any(type(x) is not bool for x in (key_present,enabled,primary_entry_present)):
        raise ValueError('explicit lookup predicates required')
    if not key_present or not enabled:
        return dict(value=None,source='gated',events=[])
    events=['lock','primary_lookup']
    if primary_entry_present:
        value=primary_value;source='primary'
    else:
        events.append('secondary_lookup')
        value=secondary_value;source='secondary'
        if value is None:
            events.append('fallback_lookup');value=fallback_value;source='fallback'
    events.append('unlock')
    return dict(value=value,source=source,events=events)


def resolve_registered_target(*, key, enabled, pairs, secondary_holder_present,
                              secondary_target, fallback_target):
    """Compose original pair search and holder dereference with resolution.

    None is the null key/payload sentinel. Pair order is significant: the first
    row with a null payload OR matching key wins. No target visibility test is
    made in the secondary holder dereference. Values remain symbolic identities.
    """
    if type(secondary_holder_present) is not bool or type(enabled) is not bool:
        raise ValueError('explicit registry predicates required')
    if len(pairs)>65535 or any(len(row)!=2 for row in pairs):
        raise ValueError('at most 65535 key/payload pairs required')
    match=None
    if key is not None and enabled:
        for index,(row_key,payload) in enumerate(pairs):
            if payload is None or row_key==key:
                match=index;break
    result=resolve_target(key_present=key is not None,enabled=enabled,
        primary_entry_present=match is not None,
        primary_value=pairs[match][1] if match is not None else None,
        secondary_value=secondary_target if secondary_holder_present else None,
        fallback_value=fallback_target)
    result['primary_index']=match
    result['lock_events']=[] if result['source']=='gated' else (
        ['outer_lock','pair_lock','pair_unlock'] +
        ([] if match is not None else ['holder_lock','holder_unlock']) + ['outer_unlock'])
    return result
