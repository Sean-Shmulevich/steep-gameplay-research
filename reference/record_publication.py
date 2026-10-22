"""Recovered nonnull-target record publication routing.

Evidence: CENTRAL_IMPULSE.md, Thread context controls record publication.
Registry preparation is opaque; this models subsequent local changes and queue
submission, not safe acquisition or execution of the publication queue.
"""


def plan_record_publication(current_target, new_target, status_word, target_flags,
                            record_index, thread_context, pool_mode):
    if any(type(v) is not int or not 0 <= v < 2**64 for v in (current_target, new_target)) or new_target == 0:
        raise ValueError('uint64 targets and nonzero new target required')
    if any(type(v) is not int or not 0 <= v < 2**32 for v in (status_word, target_flags, thread_context, pool_mode)):
        raise ValueError('uint32 fields required')
    if type(record_index) is not int or not 0 <= record_index < 0x7ffff:
        raise ValueError('encodable record index required')
    prepare = current_target != new_target
    queued = prepare and thread_context == 3 and pool_mode != 1
    pointer = current_target
    if prepare:
        target_flags = (target_flags & 0xfff80000) | (record_index + 1)
        if current_target == 0:
            pointer = new_target
            status_word = status_word & 0x7fffffff if queued else status_word | 0x80000000
    return dict(object_pointer=pointer, status_word=status_word,
                target_flags=target_flags, registry_preparation_requested=prepare,
                publication_queued=queued, lifetime_acquisition_proven=False)


def complete_record_publication(queued_identifier, current_identifier,
                                current_object, status_word):
    """Model one ready publication item after dequeue, before notification.

    The queued object is intentionally not an input: this consumer uses the
    record's current object. Notification effects and record lifetime are opaque.
    """
    if any(type(v) is not int or not 0 <= v < 2**64 for v in
           (queued_identifier, current_identifier, current_object)):
        raise ValueError('uint64 logical identifiers and object required')
    if type(status_word) is not int or not 0 <= status_word < 2**32:
        raise ValueError('uint32 status required')
    matched = queued_identifier == current_identifier
    return dict(identifier_matched=matched,
                status_word=status_word | 0x80000000 if matched else status_word,
                notify_object=current_object if matched else 0)


def transfer_publication_count(submitted, ready):
    """Model the observed zero-exchange/add handoff, with uint32 wrapping.

    This arithmetic alone does not prove the preceding publication work finished.
    """
    if any(type(v) is not int or not 0 <= v < 2**32 for v in (submitted, ready)):
        raise ValueError('uint32 counters required')
    return dict(submitted=0, ready=(ready + submitted) & 0xffffffff)
