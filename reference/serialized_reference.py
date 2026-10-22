"""Recovered tagged-reference prefixes used by the ActionKit source reader.

Evidence: ACTION_KIT_CACHE.md, Inline object prefix and reader context.
Prefix decoding does not instantiate objects or decode their payloads. Bounds
errors are this adapter's policy; the original reader uses a refill service.
"""
import struct


def decode_reference_prefix(data, offset=0):
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError('byte input required')
    if type(offset) is not int or not 0 <= offset < len(data):
        raise ValueError('offset must identify a tag byte')
    tag = data[offset]
    size = 14 if tag == 0 else 10
    if len(data) - offset < size:
        raise ValueError('incomplete reference prefix')
    if tag == 0:
        identifier, type_key = struct.unpack_from('<QI', data, offset + 1)
        result = dict(kind='inline_object', identifier=identifier,
                      type_key=type_key, skipped_byte=data[offset + 13])
    else:
        result = dict(kind='policy_reference' if tag == 1 else 'direct_reference',
                      identifier=struct.unpack_from('<Q', data, offset + 2)[0],
                      auxiliary_byte=data[offset + 1])
    result.update(tag=tag, prefix_size=size, next_offset=offset + size)
    return result


def inline_reader_context(saved_context, type_flags):
    """Context used for factory/read/post-read calls; restore saved on normal exit."""
    if type(saved_context) is not int or not 0 <= saved_context < 2**64:
        raise ValueError('uint64 logical context required')
    if type(type_flags) is not int or not 0 <= type_flags < 2**32:
        raise ValueError('uint32 type flags required')
    return dict(during_calls=0 if type_flags & 0x30000 else saved_context,
                after_normal_return=saved_context)
