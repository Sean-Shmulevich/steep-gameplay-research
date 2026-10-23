"""Vector source selection, before processor response and sample publication.

Evidence: INPUT_UPDATE_ORDER.md, Vector source configuration and cache reads.
Callbacks expose unresolved query gates. Payloads are raw little-endian float32
bytes so copies preserve NaNs, signed zero and otherwise uninterpreted lanes.
"""


def select_vector_source(mode, lane, *, vector_blocked, scalar_blocked,
                         read_vector, read_scalar):
    """Return 16 bytes; mode and lane are configuration uint32 values.

    Callback boolean results model the native low-byte truth result. Callers
    must supply bool values, not an untruncated native integer return register.
    Missing source configuration is outside this helper's contract: the source
    evaluator skips updating its prior output in that case.
    """
    for value in (mode, lane):
        if type(value) is not int or not 0 <= value < 2**32:
            raise ValueError('uint32 mode and lane required')
    out = bytes(16)
    if mode in (0, 1):
        if not vector_blocked(mode):
            out = read_vector(mode)
            if not isinstance(out, bytes) or len(out) != 16:
                raise ValueError('vector reader must return 16 bytes')
        if lane == 1:
            out = out[:4] + bytes(4) + out[8:]
        elif lane == 2:
            out = out[4:8] + bytes(4) + out[8:]
    elif mode in (2, 3):
        index = 10 if mode == 2 else 12
        if not scalar_blocked(index):
            scalar = read_scalar(index)
            if not isinstance(scalar, bytes) or len(scalar) != 4:
                raise ValueError('scalar reader must return 4 bytes')
            out = scalar + bytes(12)
    return out
