"""Recovered lazy temporary-bank preparation and selection-mask assignment.

Evidence: CENTRAL_IMPULSE.md, Temporary animation bank initialization.
Names and symbolic metadata references are authored; service bodies are supplied.
"""


def assign_binding(destination, source, *, release, copy_selection_mask):
    """Release old binding, clear it, then copy source through its owner.

    No self-assignment shortcut: native aliasing clears the source too.
    """
    if destination['value'] is not None:
        release(destination['owner'], destination['value'])
    destination['owner'] = None
    destination['value'] = None
    destination['owner'] = source['owner']
    if source['value'] is not None:
        destination['value'] = copy_selection_mask(destination['owner'], source['value'])


def prepare_temporary_bank(temporary, context, *, release_binding, copy_selection_mask,
                           release_bank, acquire_bank):
    """Initialize only when bank is None; mutate and return the descriptor.

    Owners are opaque service identities. acquire_bank(owner, binding, mode, 0).
    Metadata is represented as (base token, 160), not a dereferenced game pointer.
    Null acquisition is preserved; no success/rollback policy is invented.
    """
    if temporary['bank'] is not None:
        return temporary
    temporary['context_owner'] = context['bank_owner']
    temporary['auxiliary_owner'] = context['auxiliary_owner']
    assign_binding(temporary['binding'], context['binding'],
                   release=release_binding, copy_selection_mask=copy_selection_mask)
    mode = context['mode'] & 255
    temporary['mode'] = mode
    owner = temporary['context_owner']
    if temporary['bank'] is not None and temporary['owned']:
        release_bank(temporary['bank_owner'], temporary['bank'])
    temporary['bank_owner'] = owner
    temporary['bank'] = None
    temporary['owned'] = True
    temporary['bank'] = acquire_bank(owner, temporary['binding']['value'], mode, 0)
    temporary['metadata'] = (context['metadata_base'], 160)
    return temporary


def cleanup_temporary_bank(temporary, *, recycle_pending, release_binding, release_bank):
    """Release pending reference, binding, then owned bank; clear each handle.

    A pending reference count is uint32 and wraps on underflow, as observed.
    recycle_pending(owner, pending) queues it for reuse, not immediate destruction.
    Metadata/context fields survive. Callback exceptions have no rollback.
    """
    pending = temporary.get('pending')
    if pending is not None:
        pending['references'] = (pending['references'] - 1) & 0xffffffff
        if pending['references'] == 0:
            recycle_pending(pending['owner'], pending)
        temporary['pending'] = None
    binding = temporary['binding']
    if binding['value'] is not None:
        release_binding(binding['owner'], binding['value'])
    binding['value'] = None
    binding['owner'] = None
    if temporary['bank'] is not None and temporary['owned']:
        release_bank(temporary['bank_owner'], temporary['bank'])
    temporary['bank'] = None
    temporary['owned'] = False
    temporary['bank_owner'] = None
