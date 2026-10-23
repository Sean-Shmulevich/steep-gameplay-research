"""Recovered fallback region release bookkeeping; context operation is external.

Evidence: RESOURCE_RETIREMENT.md, Region release fallback.
No native allocation, pointer validation, OS release or callback lifetime pin.
"""


def release_metadata_region(registry, address, size, flags, record, context, *,
                            lock, unlock, release_context):
    """Clear tags before context dispatch and subtract size after normal return.

    address:uint64, size:uint32, flags:byte. registry.regions supplies retained,
    writable tag arrays. record may be None; otherwise field10 is raw uint64.
    Bit0 bypasses tag/accounting changes. A nonzero size clears at least one tag,
    otherwise floor(size/65536), and ignores terminator bits. Zero size scans
    through a high-bit tag inclusively and derives a uint32 byte size. Callback
    changes to field10 are observed by the subsequent subtraction. Services and
    storage lifetime are supplied; no exception recovery is invented.
    """
    lock(registry)
    cleared = 0
    if not flags & 1:
        if record is not None:
            high, index = address >> 32, (address >> 16) & 65535
            limit = (size >> 16) if size else 0xffffffff
            while True:
                tags = registry['regions'][high]
                terminal = bool(tags[index] & 128) if size == 0 else False
                tags[index] = 255
                index += 1
                if index == 65536:
                    index = 0
                    high = (high + 1) & 0xffffffff
                cleared += 1
                if terminal or cleared >= limit:
                    break
        if size == 0:
            size = (cleared << 16) & 0xffffffff
    release_context(context, address, size, flags)
    if not flags & 1 and record is not None:
        record['field10'] = (record['field10'] - size) & 0xffffffffffffffff
    unlock(registry)
    return dict(tags_cleared=cleared, dispatched_size=size)
