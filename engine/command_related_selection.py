"""Recovered two-pass selection within the callback submitter's follow-up.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, post-submit related-record selection.
Names below are descriptive; original subsystem/type identity is unresolved.
Caller supplies a stable iterable and fresh owner resolution for each pass.
No collection allocation, native ownership, handler body or wait is implemented.
"""


def select_related(entries, owner_key, *, resolve, handle):
    """Select matching owners, then handle entries above an unsigned threshold.

    entries contain priority:uint32 and flagged:uint8. resolve(entry) returns
    owner_key and level:uint32. First pass matches owner_key and takes maximum
    priority over flagged matches, starting at zero. Second pass resolves each
    selected entry again and handles it when level >= threshold. Ownership is
    not re-compared in the second pass. Duplicate entries are retained.

    Stable iterable storage is required by this adapter. It does not model
    native relocation, allocator growth or invalid pointers. Invalid resolved
    values raise instead of reproducing a native fault.
    """
    def uint(value, bits):
        if type(value) is not int or not 0 <= value < 1 << bits:
            raise ValueError(f'uint{bits} required')
        return value

    selected = []
    threshold = 0
    for entry in entries:
        resolved = resolve(entry)
        if resolved['owner_key'] == owner_key:
            selected.append(entry)
            if uint(entry['flagged'], 8):
                threshold = max(threshold, uint(entry['priority'], 32))
    handled = []
    for entry in selected:
        if uint(resolve(entry)['level'], 32) >= threshold:
            handle(entry)
            handled.append(entry)
    return dict(threshold=threshold, selected=selected, handled=handled,
                completion_wait_proved=False)
