"""Recovered fallback result selection over synthetic/caller-supplied records.

Evidence: CENTRAL_IMPULSE.md, Fallback result selection. No kind semantics assumed.
"""
import struct

MIN_FINITE = -3.4028234663852886e38


def select_fallback_result(records):
    """Return record index or None. Bounds/cycle refusal is an authored guard."""
    records = [bytes(r) for r in records]
    if len(records) > 65535 or any(len(r) != 24 for r in records):
        raise ValueError('bounded 24-byte records required')

    def read(index):
        if not 0 <= index < len(records):
            raise ValueError('candidate outside supplied records')
        r = records[index]
        return struct.unpack_from('<f', r, 16)[0], struct.unpack_from('<H', r, 20)[0], r[22]

    def advance(index, span):
        if not span or index + span > len(records):
            raise ValueError('span outside supplied records')
        return index + span

    def strongest(start, closing_kind):
        best = 0; weight = MIN_FINITE
        while start < len(records):
            value, span, kind = read(start)
            if kind == closing_kind:
                break
            if value > weight:
                best, weight = start, value
            start = advance(start, span)
        return best

    def resolve(index):
        seen = set()
        while True:
            if index in seen:
                raise ValueError('cyclic fallback selection')
            seen.add(index)
            _, _, kind = read(index)
            if kind == 1:
                index += 1
                if read(index)[2] == 2:
                    return None
                index = strongest(index + 1, 4)
            elif kind in (5, 7):
                index = strongest(index + 1, kind + 1)
            else:
                return index

    best = 0; weight = MIN_FINITE; root = 0
    while root < len(records):
        candidate = resolve(root)
        if candidate is None:
            return None  # aborts the whole fallback, including earlier candidates
        value = read(candidate)[0]
        if value > weight:
            best, weight = candidate, value
        root = advance(root, read(root)[1])
    return best if best < len(records) else None


def publish_fallback_result(records, context, output, *, publish_token, dispatch):
    """Expose native token store then slot-0x80 dispatch as explicit services.

    Token and provider are opaque uint64 values, never dereferenced by Python.
    Diagnostic index is authored. Providers and output construction are unresolved.
    """
    records = [bytes(r) for r in records]
    selected = select_fallback_result(records)
    if selected is not None:
        token, provider = struct.unpack_from('<QQ', records[selected])
        publish_token(context, token)
        dispatch(provider, output)
    return selected
