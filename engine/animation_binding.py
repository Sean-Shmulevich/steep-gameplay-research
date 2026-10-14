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
