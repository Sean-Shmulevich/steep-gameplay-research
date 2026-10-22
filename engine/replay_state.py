"""Version-94 serialized replay state. See LIVE_REPLAY_LEADS.md, State record.

Names are ordinal, not inferred gameplay semantics. No frame/unit conversion.
This parses the state subrecord, not its metadata prefix or a saved ghost file.
"""
import math
import struct
from .replay_spatial import decode_spatial, f32

# Divisors in serialized order, including the raw four-byte interruption below.
SCALAR_DIVISORS = (
    100,100,100,1000,10,10,10,100,10000,100,10,10,10000,10000,
    10000,100,100,10000,100,10000,10000,10000,10000,
    10,100,100,100,10000,100,100,100,100,10000,10,10,
    100,100,100,100,100,100,100,100,100,100,100,
)


def decode_state(payload, *, version, rsqrt_seed):
    if type(version) is not int or version != 94:
        raise ValueError('Only inspected state version 94 is supported')
    if not isinstance(payload, (bytes, bytearray)) or len(payload) < 259:
        raise ValueError('State subrecord requires 259 bytes')
    cursor = 0
    def take(fmt):
        nonlocal cursor
        result = struct.unpack_from('<'+fmt, payload, cursor)
        cursor += struct.calcsize('<'+fmt)
        return list(result)
    def vector():
        values = take('3f')
        if not all(math.isfinite(x) for x in values):
            raise ValueError('Nonfinite vector')
        return values
    flags = [b & 1 for b in take('24B')]
    vectors = [vector()]
    spatial = decode_spatial(payload[cursor:cursor+51],version=version,rsqrt_seed=rsqrt_seed)
    cursor += spatial['consumed']
    vectors.extend([vector(),vector()])
    scalars = []
    raw_words = []
    for index, divisor in enumerate(SCALAR_DIVISORS):
        if index == 43:
            raw_words.extend(take('I'))
        scalars.append(f32(take('h')[0]/divisor))
    vectors.append(vector())
    scalars.append(f32(take('h')[0]/10))
    tags = take('2B')
    vectors.append(vector())
    scalars.append(f32(take('h')[0]/10))
    tags.extend(take('8B'))
    raw_words.extend(take('I'))
    tags.extend(take('4B'))
    flags.append(take('B')[0] & 1)
    tags.extend(take('B'))
    raw_words.extend(take('I'))
    return {'flags':flags,'vectors':vectors,'spatial':spatial,
            'scalars':scalars,'tags':tags,'raw_words':raw_words,'consumed':cursor}
