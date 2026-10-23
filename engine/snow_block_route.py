"""Recovered local dispatch predicates, with authored callback labels.

See CENTRAL_IMPULSE.md, State-dispatch routes to gate release. This selects a
callback only: it does not run locks, callbacks, pending transitions or physics.
"""

def select_block_release_route(variant, event_code, outer_state, inner_state=None):
    """Return callback label and receiver depth, or None for the inspected skip.

    Codes are raw uint32 fields, not named gameplay enums. inner_state is needed
    only when event_code and outer_state are both zero. Depth counts +0x20 links
    below the handler's owner at +0x10; it is descriptive, not a pointer API.
    """
    if variant not in ('A', 'B'):
        raise ValueError('variant must be A or B')
    for value in (event_code, outer_state):
        if type(value) is not int or not 0 <= value < 2**32:
            raise ValueError('codes must be uint32')
    if event_code != 0:
        return None
    if outer_state == 1 and variant == 'A':
        return dict(callback='outer_one_callback', receiver_depth=1)
    if outer_state != 0:
        return None
    if type(inner_state) is not int or not 0 <= inner_state < 2**32:
        raise ValueError('inner state required on the inspected inner route')
    callback = ({5: 'release_block'} if variant == 'A' else
                {0: 'inner_zero_callback', 1: 'release_block_if_fc9', 5: 'release_block'}).get(inner_state)
    return None if callback is None else dict(callback=callback, receiver_depth=2)
