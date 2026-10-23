"""Recovered associated-reference retry protocol with explicit atomic services.

Evidence: REQUEST_COMMAND_LIFECYCLE.md, Attachment acquisition interleavings.
Services supply retained object identities, reads and uint32 compare-exchange.
"""


def acquire_attachment(*, read_source, read_count, compare_exchange):
    """Return None or the acquired token; no destination publication here.

    Read the source twice, then read the first object's count, then compare the
    saved pointers. If equal, CAS old count to old+1. Failure restarts from source.
    There is no source recheck after count reading/CAS and no zero-count rejection.
    All observed objects must remain readable throughout. This algorithm alone
    does not provide source lifetime, ABA protection or module retention.
    """
    while True:
        candidate = read_source()
        if candidate is None:
            return None
        confirmation = read_source()
        old = read_count(candidate)
        if candidate != confirmation:
            continue
        observed = compare_exchange(candidate, old, (old + 1) & 0xffffffff)
        if observed == old:
            return candidate
