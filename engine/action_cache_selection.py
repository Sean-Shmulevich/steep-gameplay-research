"""Recovered stable-snapshot input-cache selector arithmetic.

Evidence: INPUT_UPDATE_ORDER.md, Ring-index cache selectors.
No live pointer reads, lifetime pinning, allocation or scheduling is performed.
"""


def select_input_cache(offset, *, root, current_index, record_caches):
    """Select root for zero offset, otherwise ((current+offset) u32) % count.

    record_caches contains the first uint64 of each 0x440-byte native record.
    Count is uint16. Nonzero offset with zero count is rejected; the native
    path divides by zero. This API assumes the root/count remain stable.
    """
    if type(offset) is not int or not 0<=offset<1<<32:raise ValueError('uint32 offset required')
    if type(root) is not int or not 0<=root<1<<64:raise ValueError('uint64 root identity required')
    if offset==0:return dict(cache=root,record_index=None)
    if type(current_index) is not int or not 0<=current_index<1<<32:raise ValueError('uint32 current index required')
    records=tuple(record_caches)
    if not 1<=len(records)<=65535:raise ValueError('nonzero uint16 record count required')
    if any(type(v) is not int or not 0<=v<1<<64 for v in records):raise ValueError('uint64 cache identities required')
    index=((current_index+offset)&0xffffffff)%len(records)
    return dict(cache=records[index],record_index=index)
