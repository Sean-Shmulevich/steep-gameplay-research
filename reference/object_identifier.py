"""Recovered layered identifier lookup; maps and overlay contents are inputs.

Evidence: CENTRAL_IMPULSE.md, Identifier lookup and null overlay entries.
This selects logical objects only. It neither retains lifetime nor validates IDs.
"""


def resolve_object_identifier(identifier, enabled, overlay, record_target, fallback_target):
    """Resolve supplied logical uint64 values, with zero denoting null.

    overlay is an ordered sequence of [identifier, object] pairs. The native
    helper's object-match argument is zero on this route, so a null-object entry
    matches regardless of its identifier and suppresses further fallback.
    """
    values = [identifier, record_target, fallback_target]
    if type(enabled) is not bool:
        raise ValueError('enabled must be bool')
    if not isinstance(overlay, (list, tuple)) or len(overlay) > 65535:
        raise ValueError('overlay must have at most 65535 pairs')
    for pair in overlay:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError('overlay pair required')
        values.extend(pair)
    if any(type(v) is not int or not 0 <= v < 2**64 for v in values):
        raise ValueError('uint64 logical values required')
    lookups = []
    selected = None
    target = 0
    if identifier and enabled:
        lookups.append('overlay')
        for index, (key, obj) in enumerate(overlay):
            if obj == 0 or key == identifier:
                selected = index
                target = obj
                break
        else:
            lookups.append('record_map')
            target = record_target
            if target == 0:
                lookups.append('fallback_map')
                target = fallback_target
    return dict(object=target, overlay_index=selected, lookups=lookups,
                lifetime_retained=False)
