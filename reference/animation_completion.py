"""Recovered pending descriptor-group completion dispatch.

Evidence: CENTRAL_IMPULSE.md, Pending animation completion groups.
Descriptors and providers are caller-supplied; no pose sampling is substituted.
"""


def complete_pending_groups(output, *, ready, complete):
    """Consume flag bit 0 then dispatch kind-8 groups through supplied services.

    output['pending']: None or {flags, descriptors, providers}.
    descriptor: {kind, marker, provider_offset}; providers keyed by byte offset.
    ready(provider, pending) -> integer low-byte status.
    complete(provider, output, current_pending, descriptors, start, end).
    Return count is authored. Callback exceptions propagate without restoring flag.
    """
    pending = output.get('pending')
    if pending is None or not (pending['flags'] & 1):
        return 0
    pending['flags'] &= 0xfe
    descriptors = pending['descriptors']
    if len(descriptors) > 65535:
        raise ValueError('bounded descriptor list required')
    i = 0; dispatched = 0
    while i < len(descriptors):
        descriptor = descriptors[i]
        if (descriptor['kind'] & 15) != 8:
            i += 1
            continue
        current = output['pending']
        offset = descriptor['provider_offset']
        if not 0 <= offset <= 65535:
            raise ValueError('provider byte offset must be uint16')
        provider = current['providers'][offset]
        end = i + 1
        while end < len(descriptors) and descriptors[end]['marker'] != 65535:
            end += 1
        if provider is not None and (int(ready(provider, current)) & 255):
            complete(provider, output, output['pending'], descriptors, i, end)
            dispatched += 1
        i = end
    return dispatched
