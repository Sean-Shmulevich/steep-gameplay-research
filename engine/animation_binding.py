"""Recovered local binding-word operations over synthetic caller-owned mappings.

Evidence: docs/reconstruction/research/animation.md, Paired binding index swaps.
Pair identities and channel/joint semantics remain supplied by the caller. This
module neither decodes a rig nor invents the builder's pair-selection table.
"""


def swap_binding_indices(words, pairs):
    """Sequentially exchange low12 fields while preserving each word's high4.

    0xffff denotes an absent pair member. Bounds/type checks are reconstruction
    API safeguards; the native block only checks the missing-member sentinel.
    Input words are not mutated. Repeated or overlapping pairs retain order.
    """
    result = list(words)
    if any(type(word) is not int or not 0 <= word <= 65535 for word in result):
        raise ValueError('expected uint16 binding words')
    for first, second in pairs:
        if any(type(index) is not int or not 0 <= index <= 65535
               for index in (first, second)):
            raise ValueError('expected uint16 pair indices')
        if first == 0xffff or second == 0xffff:
            continue
        if first >= len(result) or second >= len(result):
            raise ValueError('pair index outside supplied binding words')
        left, right = result[first], result[second]
        result[first] = (left & 0xf000) | (right & 0x0fff)
        result[second] = (right & 0xf000) | (left & 0x0fff)
    return result


def resolve_binding_masks(class_words, class_indices):
    """Convert class labels 1/2/3 to 16-bit masks; preserve every other word.

    Evidence: animation research, Binding class-to-mask preparation. The native
    SHL AX,CL masks the shift count to five bits, then retains sixteen result
    bits. Consequently indices16..31 yield0 and index32 wraps to bit0. Caller
    supplies the three unresolved class indices; no class names are invented.
    """
    indices = tuple(class_indices)
    if len(indices) != 3:
        raise ValueError('expected three class indices')
    if any(type(index) is not int or not 0 <= index <= 65535 for index in indices):
        raise ValueError('expected uint16 class indices')
    result = []
    for word in class_words:
        if type(word) is not int or not 0 <= word <= 65535:
            raise ValueError('expected uint16 class word')
        result.append(((1 << (indices[word - 1] & 31)) & 65535)
                      if 1 <= word <= 3 else word)
    return result


def _uint(value, bits):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(f'expected uint{bits}')
    return value


def matching_channel_type(raw_type):
    """Recovered descriptor-byte switch; unknown byte values map to type8."""
    raw_type = _uint(raw_type, 8)
    return (6, 5, 5, 5, 0, 2, 3, 1)[raw_type] if raw_type < 8 else 8


def encode_channel_binding(source_index, matched_target_index, channel_hash,
                           second_variant=False, remap_word=None):
    """Encode the main four-byte mapping record, after target matching.

    Evidence: animation research, Channel classification, mask-index sources and
    swap identities. remap_word=None models first variant disabled; otherwise
    caller supplies its matched-target remap word. This is not the separate
    eight-byte special mapping record. Indices truncate as observed in native
    packing; domain validation is our API safeguard.
    """
    source = _uint(source_index, 16)
    target = _uint(matched_target_index, 16)
    channel = _uint(channel_hash, 32)
    if type(second_variant) is not bool:
        raise ValueError('expected boolean second_variant')
    extra = 0
    if remap_word is not None:
        remap = _uint(remap_word, 16)
        target, extra = remap >> 3, remap & 7
    special = second_variant and channel == 0x2c52cbb0
    packed = (source & 0xfff) | (extra << 12) | (int(special) << 15)
    return {'target_index': target, 'source_word': packed}


def inspect_channel_binding(target_index, source_word):
    """Expose packed fields without claiming joint names or flag meanings."""
    target = _uint(target_index, 16)
    word = _uint(source_word, 16)
    return {'target_index': target, 'source_index': word & 0xfff,
            'remap_bits': (word >> 12) & 7,
            'special_bit': bool(word & 0x8000)}


def find_typed_channel(hashes, descriptor_types, requested_hash, requested_type):
    """Unsigned lower bound followed by same-hash type matching.

    Evidence: ANIMATION_ENDPOINT_MOTION.md, Fallback channel lookup. Types are
    descriptor +0x20 bytes, not channel encoding bytes. Sorted/length validation
    is our API safeguard. Missing returns native uint16 sentinel 0xffff.
    """
    hashes, descriptor_types = tuple(hashes), tuple(descriptor_types)
    key, kind = _uint(requested_hash, 32), _uint(requested_type, 32)
    if len(hashes) != len(descriptor_types) or len(hashes) > 65535:
        raise ValueError('expected equal arrays with uint16 count')
    for value in hashes:
        _uint(value, 32)
    for value in descriptor_types:
        _uint(value, 8)
    if any(a > b for a, b in zip(hashes, hashes[1:])):
        raise ValueError('expected unsigned sorted channel hashes')
    first, count = 0, len(hashes)
    while count:
        half = count // 2
        middle = first + half
        if hashes[middle] < key:
            first = middle + 1
            count -= half + 1
        else:
            count = half
    while first < len(hashes) and hashes[first] == key:
        if matching_channel_type(descriptor_types[first]) == kind:
            return first
        first += 1
    return 0xffff


def select_endpoint_channels(binding_source_words=None, *, hashes=(),
                             descriptor_types=()):
    """Return two source indices or None for absent endpoint channels.

    A present binding suppresses fallback even if its index is missing. With no
    binding, look up hash zero with converted types 5 and 6 respectively.
    """
    if binding_source_words is not None:
        words = tuple(binding_source_words)
        if len(words) != 2:
            raise ValueError('expected two distinguished binding source words')
        indices = tuple(_uint(word, 16) & 0xfff for word in words)
        return tuple(None if index == 0xfff else index for index in indices)
    hashes, descriptor_types = tuple(hashes), tuple(descriptor_types)
    indices = tuple(find_typed_channel(hashes, descriptor_types, 0, kind)
                    for kind in (5, 6))
    return tuple(None if index == 0xffff else index for index in indices)
