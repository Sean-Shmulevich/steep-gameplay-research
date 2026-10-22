"""Recovered post-construction pair finalization; registration is external.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Construction pair finalization.
"""


def finalize_construction_pair(pairs, *, identity, target, target_word):
    if len(pairs)>65535 or any(len(row)!=2 for row in pairs):
        raise ValueError('bounded key/target pairs required')
    if target is None or type(target_word) is not int or not 0<=target_word<=0xffffffff:
        raise ValueError('nonnull symbolic target and uint32 word required')
    rows=[list(row) for row in pairs];match=None
    for i,(key,payload) in enumerate(rows):
        if payload==target or key==identity:
            match=i;break
    events=['lock','pair_lock','pair_unlock']
    if match is not None:
        rows[match]=rows[-1];rows.pop();events.append('swap_remove')
        if not target_word & 0x7ffff:
            events.extend(['register_identity','unlock'])
            return dict(pairs=rows,removed_index=match,target_word=target_word,
                        registration_requested=True,events=events)
    target_word |= 1<<28
    events.extend(['mark_target','unlock'])
    return dict(pairs=rows,removed_index=match,target_word=target_word,
                registration_requested=False,events=events)


def finalize_and_register(pairs, *, identity, target, target_word,
                          enabled,
                          secondary_holder_present, secondary_target,
                          target_to_identity, identity_to_target):
    """Connected finalizer and registration with supplied registry services.

    Lookup and registration use the same global enable flag. An already resolved
    identity suppresses registration even if it resolves to a different target.
    """
    from reference.animation_target_resolution import resolve_registered_target
    if type(enabled) is not bool:
        raise ValueError('explicit registry enable predicate required')
    result=finalize_construction_pair(pairs,identity=identity,target=target,target_word=target_word)
    forward=dict(target_to_identity);reverse=dict(identity_to_target)
    resolution=None;registered=False
    if result['registration_requested']:
        resolution=resolve_registered_target(key=identity,enabled=enabled,
            pairs=result['pairs'],secondary_holder_present=secondary_holder_present,
            secondary_target=secondary_target,fallback_target=reverse.get(identity))
        if resolution['value'] is None and enabled:
            result['target_word'] |= 1<<28
            reverse[identity]=target
            forward[target]=identity
            registered=True
    result.update(resolution=resolution,registered=registered,
                  target_to_identity=forward,identity_to_target=reverse)
    return result
