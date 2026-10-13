"""Recovered idle-task pop decisions from explicitly supplied observations.

See docs/reconstruction/IDLE_TASK_WORKERS.md, Tagged dummy-node pop. This is
not a concurrent queue or a memory reader. Returned CAS operations must succeed
before their follow-up writes are valid; failure requires a fresh observation.
"""

POINTER_MASK = (1 << 48) - 1


def _word(value):
    if type(value) is not int or not 0 <= value < 1 << 64:
        raise ValueError('tagged words must be uint64 integers')
    return value


def _advance(old_word, pointer):
    return (pointer & POINTER_MASK) | ((((old_word >> 48) + 1) & 0xffff) << 48)


def pop_decision(*, queue_identity, head, tail, head_next, rechecked_head,
                 tail_next=None, next_payload=None):
    """Describe one decoded branch, without applying a CAS or recycling a node.

    Arguments represent distinct loads in program order, not an atomic snapshot.
    tail_next is the later tail-link reread, needed only when head and tail point
    to the same node. next_payload is read only on the head-advance branch.
    Payload values are opaque caller-owned data; None is a valid null payload.
    """
    _word(queue_identity)
    if queue_identity > POINTER_MASK:
        raise ValueError('queue identity must fit the low 48-bit representation')
    for value in (head, tail, head_next, rechecked_head):
        _word(value)
    if head != rechecked_head:
        return dict(action='retry')
    if head_next == queue_identity:
        return dict(action='empty')
    old_dummy = head & POINTER_MASK
    if old_dummy == tail & POINTER_MASK:
        _word(tail_next)
        if tail_next & POINTER_MASK == queue_identity:
            return dict(action='retry')
        return dict(action='help_tail', expected=tail,
                    desired=_advance(tail, tail_next), after_cas='retry')
    return dict(action='advance_head', expected=head,
                desired=_advance(head, head_next),
                on_success=dict(return_node=old_dummy,
                                write_payload=next_payload),
                on_failure='retry')
