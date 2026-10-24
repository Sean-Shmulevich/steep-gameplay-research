"""Local vector routing; CENTRAL_IMPULSE.md, Motion vector dispatcher contract.

No native lock, object resolution, deferred transitions or live game calls.
"""


def _state(value):
    if type(value) is not int or not 0 <= value <= 0xffffffff:
        raise ValueError('uint32 state required')
    return value


def select_vector_route(current_mode, outer_state=None, inner_state=None):
    """Return an authored route label, receiver depth and native return value.

    Nonzero mode preserves the caller's vector; unsupported mode-zero states
    zero it. These outcomes must not be conflated. Only needed states are read.
    """
    if _state(current_mode) != 0:
        return dict(route='preserve',receiver_depth=0,return_value=1)
    outer = _state(outer_state)
    if outer == 1:
        route, depth = 'projection_outer_one', 1
    elif outer == 3:
        route, depth = 'direction_outer_three', 1
    elif outer == 0 and _state(inner_state) == 5:
        route, depth = 'projection_inner_five', 2
    else:
        route, depth = 'zero', 0
    return dict(route=route,receiver_depth=depth,return_value=0)


def dispatch_vector(current_mode, outer_state, inner_state, vector, invoke):
    """Apply local routing with an external (label, depth, vector) service.

    vector is a caller-owned four-lane mutable buffer. Callback return ignored.
    The native epilogue may run deferred work; this helper does not model it.
    """
    if len(vector) != 4:
        raise ValueError('four-lane mutable output required')
    decision=select_vector_route(current_mode,outer_state,inner_state)
    route=decision['route']
    if route=='zero':
        vector[:]=[0.0]*4
    elif route!='preserve':
        invoke(route,decision['receiver_depth'],vector)
    return decision['return_value']
