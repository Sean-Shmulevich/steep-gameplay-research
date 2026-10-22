"""Null-target record recycling and free-slot initialization.

Evidence: CENTRAL_IMPULSE.md, Record slot reuse and identity. These functions
model inspected local operations; they do not operate a live registry or locks.
"""


def recycle_null_record(identifier, status_word, record_count, slot, free_head):
    """Plan reclamation of a caller-confirmed null-target record.

    free_head and returned next_free use -1 as the empty-list marker. The native
    record's count field becomes the free-list link after successful recycling.
    Map erasure is an effect request, not executed by this function.
    """
    if type(identifier) is not int or not 0 <= identifier < 2**64:
        raise ValueError('uint64 identifier required')
    if any(type(x) is not int or not 0 <= x < 2**32 for x in (status_word, record_count)):
        raise ValueError('uint32 status and count required')
    if type(slot) is not int or not 0 <= slot < 16384:
        raise ValueError('page slot required')
    if type(free_head) is not int or not -1 <= free_head < 16384:
        raise ValueError('free-list head required')
    accepted = not (status_word & ((1 << 26) | (1 << 24) | 0xffffff)) and record_count == 0
    recycled = accepted and identifier != 0
    erase_identifier = recycled and not (0xf0000000 <= identifier <= 0xf7ffffff) and not status_word & (1 << 28)
    return dict(status_word=status_word | (1 << 26) if accepted else status_word,
                count_or_link=(free_head & 0xffffffff) if recycled else record_count,
                free_head=slot if recycled else free_head, recycled=recycled,
                erase_identifier=bool(erase_identifier))


def initialize_reused_record(identifier, next_free):
    """Initialize a popped slot before binding or ownership acquisition.

    The local initializer clears both counter/status words and overwrites the
    identifier. No generation counter is incremented within this record.
    """
    if type(identifier) is not int or not 0 <= identifier < 2**64:
        raise ValueError('uint64 identifier required')
    if type(next_free) is not int or not -1 <= next_free < 16384:
        raise ValueError('next free slot required')
    return dict(object_pointer=0, record_count=0, status_word=0,
                identifier=identifier, free_head=next_free)
