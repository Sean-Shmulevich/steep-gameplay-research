"""Recovered channel-handle resolution; no retained lifetime or synchronization."""
from reference.ground_response_pose import pose_channel_index


def resolve_channel_handle(raw_pointer, status_word, thread_mask, cached_index,
                           cached_generation, component_generation, entries, key):
    """Resolve supplied control-record bits and refresh a channel cache if needed.

    Pointer arithmetic is modeled on integers for synthetic inspection. A nonzero
    result is not proof that storage is mapped, live or retained. No reference
    counter changes occur in this resolver. Caller supplies table/generation data
    belonging to the resolved component; null resolution ignores those fields.
    """
    if any(type(v) is not int or not 0 <= v < 2**64 for v in (raw_pointer, thread_mask)):
        raise ValueError('uint64 pointer/mask required')
    if type(status_word) is not int or not 0 <= status_word < 2**32:
        raise ValueError('uint32 status required')
    if any(type(v) is not int or not 0 <= v <= 65535 for v in (cached_index, cached_generation)):
        raise ValueError('uint16 cache fields required')
    mask = (2**64 - 1) if status_word & (1 << 31) else thread_mask
    pointer = raw_pointer & mask
    refreshed = False
    if pointer:
        if type(component_generation) is not int or not 0 <= component_generation <= 65535:
            raise ValueError('uint16 component generation required')
        if cached_generation != component_generation:
            cached_index = pose_channel_index(entries, key)
            cached_generation = component_generation
            refreshed = True
    return dict(pointer=pointer, cached_index=cached_index,
                cached_generation=cached_generation, refreshed=refreshed,
                lifetime_retained=False)


def invalidate_control_record(indexed_object_flags, target_object_flags, raw_pointer,
                              status_word, record_count):
    """Model the inspected indexed-record invalidation, without touching a process.

    Caller supplies the record at the decoded slot. Its raw pointer may identify
    a different object than the lookup object, so target flags are explicit.
    Counters are not retention guarantees. This models the lock-free helper's
    serial result; registry mapping/lifetime and concurrent CAS retries are absent.
    """
    words = (indexed_object_flags, target_object_flags, status_word, record_count)
    if any(type(value) is not int or not 0 <= value < 2**32 for value in words):
        raise ValueError('uint32 flags, status and count required')
    if type(raw_pointer) is not int or not 0 <= raw_pointer < 2**64:
        raise ValueError('uint64 logical pointer required')
    encoded = indexed_object_flags & 0x7ffff
    slot = None if encoded == 0 else [(encoded - 1) >> 14, (encoded - 1) & 0x3fff]
    invalidated = slot is not None and raw_pointer != 0
    if invalidated:
        target_object_flags &= 0xfff80000
        raw_pointer = 0
        status_word &= 0x7fffffff
    return dict(slot=slot, pointer=raw_pointer, status_word=status_word,
                record_count=record_count, target_object_flags=target_object_flags,
                invalidated=invalidated)
