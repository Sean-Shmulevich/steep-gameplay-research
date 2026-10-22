"""Recovered target/backing association writes during holder retirement.

See docs/reconstruction/ANIMATION_CONTEXT_RETIREMENT.md, target service section.
Keys are caller-supplied symbolic identities, never reusable native pointers.
"""


def record_target_association(target_to_backing, backing_to_target, *,
                              target_key, backing_key, locked_target_word):
    """Copy two supplied maps and report the service's ordered local effects.

    locked_target_word is the value re-read after lock acquisition. Native map
    allocation, TLS storage and synchronization remain external services.
    """
    if type(locked_target_word) is not int or not 0 <= locked_target_word <= 0xffffffff:
        raise ValueError('uint32 locked target word required')
    forward=dict(target_to_backing);reverse=dict(backing_to_target)
    events=['lock']
    if locked_target_word & (1 << 28):
        forward[target_key]=backing_key
        reverse[backing_key]=target_key
        events.extend(['set_tls_context','write_target_to_backing','clear_tls_context',
                       'set_tls_context','write_backing_to_target','clear_tls_context'])
    events.append('unlock')
    return dict(target_to_backing=forward,backing_to_target=reverse,events=events)


def remove_target_association(target_to_backing, backing_to_target, *,
                              target_key, target_word, enabled):
    """Recovered removal gate; caller owns synchronization.

    None denotes a null mapped identity. A nonzero low-19 field suppresses map
    removal but does not suppress clearing bit 28 while globally enabled.
    """
    if type(enabled) is not bool or type(target_word) is not int or not 0<=target_word<=0xffffffff:
        raise ValueError('enabled predicate and uint32 target word required')
    forward=dict(target_to_backing);reverse=dict(backing_to_target)
    events=[];backing=None
    if enabled:
        if not target_word & 0x7ffff:
            events.append('lookup_target_to_backing')
            backing=forward.get(target_key)
            forward.pop(target_key,None)
            events.extend(['set_tls_context','erase_target_to_backing','clear_tls_context'])
            if backing is not None:
                reverse.pop(backing,None)
                events.extend(['set_tls_context','erase_backing_to_target','clear_tls_context'])
        target_word &= ~(1<<28)
    return dict(target_to_backing=forward,backing_to_target=reverse,
                target_word=target_word,backing=backing,events=events)
