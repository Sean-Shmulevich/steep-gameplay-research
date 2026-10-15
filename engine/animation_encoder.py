"""Inverse of the animation decoder: serialized channel and clip-body writers.

Evidence: ANIMATION_SERIALIZED_CHANNELS.md, ANIMATION_CONTAINER.md and the
format guides cited by engine/animation_decoder.py. This is a data-only modding
aid with no game bytes or addresses. Layouts and quantisation constants are the
decoder's; the encoder introduces no new format claims.

Two layers are kept apart. The structural layer (parse_channel/build_channel,
parse_clip/build_clip) keeps raw sample bytes and is byte-exact for every
framed record. The value layer (decode_sample/encode_value) is lossy for
quantised formats; encode_value(decode_sample(raw)) reproduces raw for every
word the omitted-lane rule can distinguish and returns the supplied original
bytes otherwise (the `like` argument).
"""
import math
import struct
from .animation_channel_framing import ELEMENT_BYTES, frame_serialized_channel
from .animation_container import parse_clip_body
from .animation_decoder import (quaternion_smallest_three32, quaternion_smallest_three48,
                                quaternion_smallest_three64, quaternion_three_floats,
                                quaternion_z16)

OFFSET = .7071067690849304
SCALE_10 = .0013837706064805388
SCALE_15 = 4.316100603318773e-05
SCALE_20 = 1.3487017440638738e-06
SCALE_S8 = .008

# Value-decoding families keyed by serialized tag (family*3 + time format).
KINDS = {0: 'f4'}
for _base, _kind in ((9, 's32'), (12, 's48'), (15, 's64'), (21, 'z16'), (24, 'sfl'), (27, 'vec3'), (39, 's8')):
    for _t in range(3):
        KINDS[_base + _t] = _kind
KINDS[54] = 'u32'
KINDS[66] = 'u64'
# Keep these identical to registered_channel_decoder's supported list.
VALUE_ENCODINGS = tuple(sorted(KINDS))
QUANTISED = ('s32', 's48', 's64', 'z16', 'sfl', 's8')
QUATERNION_KINDS = ('f4', 's32', 's48', 's64', 'z16', 'sfl')


def _check_encoding(encoding):
    if type(encoding) is not int or not 0 <= encoding <= 255:
        raise ValueError('expected uint8 encoding')
    family, time_format = divmod(encoding, 3)
    if family not in ELEMENT_BYTES:
        raise ValueError('unsupported serialized channel framing')
    return family, time_format


def sample_bytes(encoding):
    return ELEMENT_BYTES[_check_encoding(encoding)[0]]


def _f32(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('expected finite value')
    try:
        return struct.unpack('<f', struct.pack('<f', value))[0]
    except OverflowError:
        raise ValueError('value outside float32 range') from None


def _index(value, scale, limit):
    return min(limit, max(0, round((value+OFFSET)/scale)))


def _unit(value):
    q = [float(v) for v in value[:4]]
    if len(q) != 4 or not all(math.isfinite(v) for v in q):
        raise ValueError('expected four finite quaternion components')
    norm = math.sqrt(sum(v*v for v in q))
    if norm == 0:
        raise ValueError('zero quaternion cannot be encoded')
    if abs(norm-1) > 1e-6:
        q = [v/norm for v in q]
    missing = max(range(4), key=lambda i: (abs(q[i]), i))
    if q[missing] < 0:
        q = [-v for v in q]
    return q, missing, [v for i, v in enumerate(q) if i != missing]


def encode_smallest_three32(value):
    q, missing, c = _unit(value)
    a, b, d = (_index(v, SCALE_10, 1023) for v in c)
    return (missing << 30) | (a << 20) | (b << 10) | d


def encode_smallest_three48(value):
    q, missing, c = _unit(value)
    words = [_index(v, SCALE_15, 32767) for v in c]
    words[0] |= (missing & 1) << 15
    words[1] |= (missing >> 1) << 15
    return tuple(words)


def encode_smallest_three64(value):
    q, missing, c = _unit(value)
    a, b, d = (_index(v, SCALE_20, 0xfffff) for v in c)
    packed = (missing << 62) | (a << 40) | (b << 20) | d
    return (packed >> 32, packed & 0xffffffff)


def encode_three_floats(value):
    q, missing, c = _unit(value)
    words = [struct.unpack('<I', struct.pack('<f', _f32(v)))[0] for v in c]
    words[0] = (words[0] & ~1) | (missing & 1)
    words[1] = (words[1] & ~1) | (missing >> 1)
    return tuple(words)


def encode_z16(value, tolerance=1e-5):
    """Encode a restricted (0,0,z,w) rotation; nonzero x/y beyond tolerance is rejected."""
    if len(value) < 4 or not all(math.isfinite(v) for v in value[:4]):
        raise ValueError('expected four finite quaternion components')
    if abs(value[0]) > tolerance or abs(value[1]) > tolerance:
        raise ValueError('encoding 21 family stores only z/w rotation')
    z, w = float(value[2]), float(value[3])
    norm = math.hypot(z, w)
    if norm == 0:
        raise ValueError('zero quaternion cannot be encoded')
    z, w = z/norm, w/norm
    if abs(z) > abs(w):
        stored, missing, flag = w, z, 32768
    else:
        stored, missing, flag = z, w, 0
    if missing < 0:
        stored = -stored
    return flag | _index(stored, SCALE_15, 32767)


def decode_sample(encoding, raw):
    """Decode one raw sample with the decoder's own functions (exact radicands)."""
    kind = KINDS.get(encoding)
    if kind is None:
        raise ValueError('no value decoder for encoding')
    raw = bytes(raw)
    if len(raw) != sample_bytes(encoding):
        raise ValueError('sample length mismatch')
    if kind == 'f4':
        value = list(struct.unpack('<4f', raw))
    elif kind == 's32':
        value = quaternion_smallest_three32(struct.unpack('<I', raw)[0])
    elif kind == 's48':
        value = quaternion_smallest_three48(struct.unpack('<3H', raw))
    elif kind == 's64':
        value = quaternion_smallest_three64(struct.unpack('<2I', raw))
    elif kind == 'z16':
        value = quaternion_z16(struct.unpack('<H', raw)[0])
    elif kind == 'sfl':
        value = quaternion_three_floats(struct.unpack('<3I', raw))
    elif kind == 'vec3':
        value = list(struct.unpack('<3f', raw))+[0.0]
    elif kind == 's8':
        return [_f32(struct.unpack('<b', raw)[0]*_f32(SCALE_S8))]
    elif kind == 'u32':
        return [struct.unpack('<I', raw)[0]]
    else:
        return [struct.unpack('<Q', raw)[0]]
    if not all(math.isfinite(v) for v in value):
        raise ValueError('nonfinite sample')
    return value


def encode_value(encoding, value, like=None):
    """Quantise one decoded value into raw sample bytes.

    `like`, if supplied, is original raw bytes: when they already decode to
    exactly `value`, they are returned unchanged. That keeps unused bits and
    near-tie omitted-lane choices byte-exact without guessing them.
    """
    kind = KINDS.get(encoding)
    if kind is None:
        raise ValueError('no value encoder for encoding')
    value = list(value)
    if like is not None:
        try:
            if decode_sample(encoding, like) == value:
                return bytes(like)
        except (ValueError, struct.error):
            pass
    if kind == 'f4':
        if len(value) != 4:
            raise ValueError('expected four lanes')
        return struct.pack('<4f', *(_f32(v) for v in value))
    if kind == 's32':
        return struct.pack('<I', encode_smallest_three32(value))
    if kind == 's48':
        return struct.pack('<3H', *encode_smallest_three48(value))
    if kind == 's64':
        return struct.pack('<2I', *encode_smallest_three64(value))
    if kind == 'z16':
        return struct.pack('<H', encode_z16(value))
    if kind == 'sfl':
        return struct.pack('<3I', *encode_three_floats(value))
    if kind == 'vec3':
        if len(value) not in (3, 4) or (len(value) == 4 and value[3] != 0):
            raise ValueError('vector lane 3 must be absent or zero')
        return struct.pack('<3f', *(_f32(v) for v in value[:3]))
    if kind == 's8':
        if len(value) != 1 or not math.isfinite(value[0]):
            raise ValueError('expected one finite scalar')
        return struct.pack('<b', min(127, max(-128, round(value[0]/SCALE_S8))))
    if len(value) != 1 or type(value[0]) is not int:
        raise ValueError('expected one integer lane')
    limit = 0xffffffff if kind == 'u32' else 0xffffffffffffffff
    if not 0 <= value[0] <= limit:
        raise ValueError('integer lane out of range')
    return struct.pack('<I' if kind == 'u32' else '<Q', value[0])


def choose_mask_mode(ticks):
    """Smallest tick shift (finest) and mask size that can hold strictly increasing ticks."""
    ticks = list(ticks)
    if not ticks or ticks[0] != 0 or any(a >= b for a, b in zip(ticks, ticks[1:])):
        raise ValueError('mask ticks must start at zero and strictly increase')
    for shift in range(4):
        if all(t % (1 << shift) == 0 for t in ticks):
            size = (ticks[-1] >> shift)//8+1
            if size <= 63:
                return size | (shift << 6)
    raise ValueError('ticks do not fit a mask time layout')


# Runtime sample alignment per supported tag; time layout follows the tag modulo three.
ALIGNMENT = {0: 16, 9: 4, 10: 4, 11: 4, 12: 2, 13: 2, 14: 2, 15: 4, 16: 4, 17: 4, 21: 2, 22: 2, 23: 2,
             24: 4, 25: 4, 26: 4, 27: 4, 28: 4, 29: 4, 39: 1, 40: 1, 41: 1, 54: 4, 66: 8}


def default_allocation(encoding, ticks, mode=None):
    """Opaque allocation word for new records.

    In the checked corpus it equals the size of the decoder's runtime payload
    (unpack_serialized_channel) for every supported record; encodings without a
    runtime layout fall back to count times sample width. This is an observed
    relation, not a recovered meaning.
    """
    family, tf = _check_encoding(encoding)
    count, stride = len(ticks), ELEMENT_BYTES[family]
    align = ALIGNMENT.get(encoding)
    if align is None:
        return count*stride
    if tf == 0:
        head = (count+align) & ~(align-1)
    elif tf == 1:
        head = ((2 if count < 256 else 4)+2*(count-1)+align-1) & ~(align-1)
    else:
        size = (choose_mask_mode(ticks) if mode is None else mode) & 63
        head = (size+1+align) & ~(align-1)
    return head+count*stride


def parse_channel(data, offset=0):
    """Split one serialized record into times, raw samples and opaque allocation.

    ticks always lists the first implicit zero key. Mask records keep their mode
    byte so size and shift are reproduced exactly.
    """
    data = memoryview(data)
    framed = frame_serialized_channel(data, offset)
    encoding, count, tf = framed['encoding'], framed['count'], framed['time_format']
    start = offset+9
    if tf == 2:
        mode = framed['mode'];size = mode & 63
        mask = int.from_bytes(data[start+1:start+1+size], 'little')
        ticks = [p << (mode >> 6) for p in range(size*8) if (mask >> p) & 1]
    else:
        mode = None
        if tf == 0:
            stored = list(data[start:start+count-1])
        else:
            stored = list(struct.unpack_from('<%dH' % (count-1), data, start))
        ticks = [0]+stored
    stride = framed['sample_bytes'];at = framed['sample_offset']
    return {'encoding': encoding, 'allocation': framed['opaque_allocation'], 'mode': mode,
            'ticks': ticks, 'samples': [bytes(data[at+stride*i:at+stride*(i+1)]) for i in range(count)],
            'consumed': framed['consumed']}


def build_channel(channel):
    """Serialize a channel dict; the inverse of parse_channel."""
    encoding = channel['encoding'];family, tf = _check_encoding(encoding)
    ticks, samples = list(channel['ticks']), list(channel['samples'])
    count = len(ticks)
    if count == 0 or len(samples) != count:
        raise ValueError('channel needs equal nonzero tick and sample counts')
    stride = ELEMENT_BYTES[family]
    if any(len(s) != stride for s in samples):
        raise ValueError('sample width mismatch')
    allocation = channel.get('allocation')
    if allocation is None:
        allocation = default_allocation(encoding, ticks, channel.get('mode'))
    if type(allocation) is not int or not 0 <= allocation <= 0xffffffff:
        raise ValueError('expected uint32 allocation')
    out = bytearray([encoding])+struct.pack('<II', allocation, count)
    if tf == 2:
        mode = channel.get('mode')
        if mode is None:
            mode = choose_mask_mode(ticks)
        size, shift = mode & 63, mode >> 6
        if size == 0 or any(t % (1 << shift) for t in ticks) or ticks[0] != 0 or any(a >= b for a, b in zip(ticks, ticks[1:])):
            raise ValueError('ticks do not fit the mask mode')
        mask = 0
        for t in ticks:
            if (t >> shift) >= size*8:
                raise ValueError('tick beyond mask size')
            mask |= 1 << (t >> shift)
        out.append(mode);out += mask.to_bytes(size, 'little')
    else:
        limit = 255 if tf == 0 else 65535
        if ticks[0] != 0 or count > limit or any(not 0 <= t <= limit for t in ticks) or any(a > b for a, b in zip(ticks, ticks[1:])):
            raise ValueError('key times outside the time format')
        if tf == 0:
            out += bytes(ticks[1:])
        else:
            out += struct.pack('<%dH' % (count-1), *ticks[1:])
    for s in samples:
        out += s
    return bytes(out)


def channel_values(channel):
    return [decode_sample(channel['encoding'], s) for s in channel['samples']]


def make_channel(encoding, ticks, values, *, allocation=None, mode=None, like=None):
    """Build a channel dict from decoded values; `like` is an optional parsed channel
    of equal key count whose unchanged raw samples are kept byte-exact."""
    values = list(values)
    if len(values) != len(list(ticks)):
        raise ValueError('ticks and values differ in length')
    if like is not None and len(like['samples']) != len(values):
        raise ValueError('like channel has a different key count')
    samples = [encode_value(encoding, v, None if like is None else like['samples'][i])
               for i, v in enumerate(values)]
    return {'encoding': encoding, 'allocation': allocation, 'mode': mode,
            'ticks': list(ticks), 'samples': samples}


def parse_clip(body):
    """Decode a clip body into opaque prefix bytes plus editable tracks.

    The prefix (header, events, bindings, opaque blob, channel count) is carried
    verbatim, so edits must keep the track count. Shared references (tag 254)
    are kept as {'shared_reference': n}.
    """
    body = bytes(body)
    info = parse_clip_body(body)
    tracks = []
    for t in info['tracks']:
        if 'shared_track_reference' in t:
            tracks.append({'shared_reference': t['shared_track_reference'],
                           'binding_hash': t['binding_hash']})
        else:
            channel = parse_channel(body, t['serialized_start'])
            channel['binding_hash'] = t['binding_hash']
            tracks.append(channel)
    first = info['tracks'][0]['serialized_start'] if info['tracks'] else len(body)
    return {'prefix': body[:first], 'tracks': tracks}


def build_track(track):
    """Serialize one parse_clip track: a channel or a shared-reference record."""
    if 'shared_reference' in track:
        return bytes([254])+struct.pack('<I', track['shared_reference'])
    return build_channel(track)


def build_clip(clip):
    return bytes(clip['prefix'])+b''.join(build_track(t) for t in clip['tracks'])


def _find_track(clip, track):
    tracks = clip['tracks']
    if type(track) is int and 0 <= track < len(tracks):
        return track
    raise ValueError('track index out of range')


def map_track_values(clip, track, function):
    """Return a clip copy whose selected track has every key value replaced by
    function(value). Unchanged values keep their original bytes."""
    index = _find_track(clip, track)
    source = clip['tracks'][index]
    if 'shared_reference' in source:
        raise ValueError('shared-reference track has no local values')
    values = channel_values(source)
    changed = []
    for v in values:
        new = list(function(list(v)))
        # Differences below any format's quantum keep the original bytes.
        same = len(new) == len(v) and all(abs(a-b) < 1e-7 for a, b in zip(new, v))
        changed.append(v if same else new)
    channel = make_channel(source['encoding'], source['ticks'], changed,
                           allocation=source['allocation'], mode=source['mode'], like=source)
    channel['binding_hash'] = source.get('binding_hash')
    tracks = list(clip['tracks']);tracks[index] = channel
    return {'prefix': clip['prefix'], 'tracks': tracks}


def scale_quaternion_rotation(q, factor):
    """Scale rotation angle about the quaternion's own axis; identity-preserving."""
    x, y, z, w = (float(v) for v in q)
    if w < 0:
        x, y, z, w = -x, -y, -z, -w
    sine = math.sqrt(x*x+y*y+z*z)
    if sine < 1e-12:
        return [0.0, 0.0, 0.0, 1.0]
    angle = 2*math.atan2(sine, w)*factor
    s = math.sin(angle/2)/sine
    return [x*s, y*s, z*s, math.cos(angle/2)]


def scale_rotation_amplitude(clip, track, factor):
    """Scale one rotation track's angle (factor 0 holds identity, 2 doubles every swing).

    Visible-swap helper: decoded clip in, decoded clip out; pass the result to
    build_clip. Only quaternion encodings are accepted; a restricted z/w track
    stays restricted because scaling preserves the axis.
    """
    index = _find_track(clip, track)
    source = clip['tracks'][index]
    if 'shared_reference' in source or KINDS.get(source['encoding']) not in QUATERNION_KINDS:
        raise ValueError('track is not a local quaternion channel')
    if not math.isfinite(factor):
        raise ValueError('expected finite factor')
    if factor == 1:
        return {'prefix': clip['prefix'], 'tracks': list(clip['tracks'])}
    return map_track_values(clip, index, lambda q: scale_quaternion_rotation(q, factor))
