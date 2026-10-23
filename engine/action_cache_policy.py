"""Recovered cache-index decision policy with an explicit unresolved query.

Evidence: INPUT_UPDATE_ORDER.md, Cache-index writer and selection policy.
This computes a decision, not callback effects, pointer lifetime or scheduling.
"""


def choose_input_cache(*, scan_begin, scan_end, fallback_flag, record_count,
                       record_ids, query):
    """Return selected index or None, queried indices, and final-notification flag.

    Query receives each record's uint32 ID and returns its uint32 result.
    Zero stops the scan. IDs and bounds are caller-supplied snapshots; the
    original may reread mutable metadata. No index assignment or notification
    is performed here. Missing scanned records raise rather than reading past
    memory. Record IDs may include slots beyond the active record count.
    """
    for value in (scan_begin, scan_end, fallback_flag):
        if type(value) is not int or not 0 <= value < 1 << 32:
            raise ValueError('uint32 scan bounds and fallback flag required')
    if type(record_count) is not int or not 0 <= record_count <= 65535:
        raise ValueError('uint16 record count required')
    ids = tuple(record_ids)
    if any(type(v) is not int or not 0 <= v < 1 << 32 for v in ids):
        raise ValueError('uint32 record IDs required')
    queried = []
    for index in range(scan_begin, scan_end):
        if index >= len(ids):
            raise ValueError('scan references an unavailable record')
        queried.append(index)
        result = query(ids[index])
        if type(result) is not int or not 0 <= result < 1 << 32:
            raise ValueError('query must return a uint32 result')
        if result == 0:
            return dict(selected_index=index if index < record_count else None,
                        queried_indices=tuple(queried), final_notifications=False)
    if fallback_flag:
        selected = scan_end if scan_end < record_count else None
    else:
        selected = 0 if record_count else None
    return dict(selected_index=selected, queried_indices=tuple(queried),
                final_notifications=not bool(fallback_flag))
