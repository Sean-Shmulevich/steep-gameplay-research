"""Recovered record-insertion counter updates, not allocation or device discovery.

Evidence: INPUT_UPDATE_ORDER.md, Record categories and counter producers.
"""


def count_inserted_cache(*, kind, scan_begin, scan_end, fallback_count,
                         kind9_count, record_id):
    """Update uint32 counters and derive this record's query ID.

    record_id is the supplied uint16 identifier. Kinds 2/6/7/8/10 retain it
    as a uint32 query ID; other kinds use 0xffffffff. No record storage,
    count/capacity allocation, nested configuration or scheduling is modeled.
    """
    for value in (kind, scan_begin, scan_end, fallback_count, kind9_count):
        if type(value) is not int or not 0 <= value < 1 << 32:
            raise ValueError('uint32 kind and counters required')
    if type(record_id) is not int or not 0 <= record_id <= 65535:
        raise ValueError('uint16 record ID required')
    query_id = 0xffffffff
    if kind == 0:
        scan_begin = (scan_begin + 1) & 0xffffffff
        scan_end = (scan_end + 1) & 0xffffffff
    elif kind in (2, 6, 7, 8, 10):
        scan_end = (scan_end + 1) & 0xffffffff
        query_id = record_id
    else:
        fallback_count = (fallback_count + 1) & 0xffffffff
        if kind == 9:
            kind9_count = (kind9_count + 1) & 0xffffffff
    return dict(scan_begin=scan_begin, scan_end=scan_end,
                fallback_count=fallback_count, kind9_count=kind9_count,
                query_id=query_id)
