"""Recovered region-span retirement traversal with supplied owner operations.

Evidence: RESOURCE_RETIREMENT.md, Region-span retirement traversal.
This does not implement native memory release, TLS initialization or safe unload.
"""


def retire_metadata_regions(registry, record, context, *, lock, unlock,
                            ensure_initialized, address_limit, fallback):
    """Scan 64-KiB tags, dispatch inclusive high-bit-terminated spans under lock.

    registry.regions maps high32 to None or a 65536-byte table. registry.override
    is None or callable(address, uint32_size, reason2, record, context). The
    fallback adds registry as first argument. record.index is the current byte;
    record.field10 is cleared after traversal, before unlocking.

    Caller retains tables and supplies initialized bounds. Missing tables inside
    a matched span are invalid, not implicit terminators. Callback changes are
    observed at subsequent outer reads. The inner span scan uses the region map
    captured for that span, may cross high32 boundaries and does not recheck tag
    ownership. Native reason2 semantics and callback effects remain external.
    """
    lock(registry)
    high = 0
    spans = 0
    while True:
        ensure_initialized()
        if high >= address_limit() >> 32:
            break
        regions = registry['regions']
        if regions.get(high) is not None:
            index = 0
            while index < 65536:
                regions = registry['regions']
                tag = regions[high][index]
                if tag & 127 == record['index']:
                    address = ((high << 32) + (index << 16)) & 0xffffffffffffffff
                    cursor_high, cursor_index, count = high, index, 0
                    while True:
                        current = regions[cursor_high][cursor_index]
                        count += 1
                        cursor_index += 1
                        if cursor_index == 65536:
                            cursor_index = 0
                            cursor_high = (cursor_high + 1) & 0xffffffff
                        if current >= 128 or count == 0xffffffff:
                            break
                    size = (count << 16) & 0xffffffff
                    override = registry['override']
                    if override is not None:
                        override(address, size, 2, record, context)
                    else:
                        fallback(registry, address, size, 2, record, context)
                    spans += 1
                    index += count
                else:
                    index += 1
        high += 1
    record['field10'] = 0
    unlock(registry)
    return dict(spans_dispatched=spans)
