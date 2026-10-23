"""Recovered allocator front-end and context-selection policy, not a heap.

Evidence: REQUEST_COMMAND_LIFECYCLE.md, Allocator dispatch and context selection.
All allocator objects, globals and unresolved calls are supplied services/tokens.
No native memory access, alignment guarantee, free operation or lifetime pin.
"""


def _uint(value, bits, name):
    if type(value) is not int or not 0 <= value < 2**bits:
        raise ValueError(f'{name} must be uint{bits}')
    return value


def select_allocation_context(size, alignment, source, *, special_a, special_b,
                              coarse_source, override_source, resolve):
    """Select a context token using known equality gates and unsigned arithmetic.

    The resolver is skipped for either special source. Its nonzero result wins.
    Otherwise compare (-size)&65535 with size>>4, or size>>6 when source equals
    coarse_source; a strict less-than selects override_source. The identities and
    meaning of these contexts remain supplied, not inferred allocator classes.
    """
    _uint(size, 32, 'size'); _uint(alignment, 32, 'alignment')
    for value in (source, special_a, special_b, coarse_source, override_source):
        _uint(value, 64, 'context token')
    if source != special_a and source != special_b:
        resolved = _uint(resolve(size, alignment, source), 64, 'resolved context')
        if resolved:
            return resolved
    threshold = size >> (6 if source == coarse_source else 4)
    return override_source if ((-size) & 0xffff) < threshold else source


def allocate_bytes(size, alignment, context, *, current_allocator,
                   allocate_default, allocate_aligned, recover):
    """Dispatch a request; optionally retry once after a null result.

    alignment <=16 uses allocate_default(allocator,size,context). Larger unsigned
    values use allocate_aligned(allocator,size,alignment,context). Read the current
    allocator again on retry. recover(1,size,0,0,0) is called only after the first
    null result; only its low byte decides whether to retry. Zero size returns
    zero without invoking any service. Exceptions propagate as authored Python
    behavior; native allocator/recovery failures and synchronization are unknown.
    """
    _uint(size, 32, 'size'); _uint(alignment, 32, 'alignment'); _uint(context, 64, 'context')
    if size == 0:
        return 0
    retried = False
    while True:
        allocator = current_allocator()
        pointer = (allocate_default(allocator, size, context) if alignment <= 16
                   else allocate_aligned(allocator, size, alignment, context))
        _uint(pointer, 64, 'allocation result')
        if pointer or retried:
            return pointer
        decision = recover(1, size, 0, 0, 0)
        if not isinstance(decision, int):
            raise ValueError('recovery result must be an integer')
        if not decision & 255:
            return 0
        retried = True
