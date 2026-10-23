"""Recovered loading-thread destruction insertion, not successful disposal.

Evidence: LOADING_THREAD_LIFECYCLE.md, Executable loading destruction insertion.
Caller supplies retained owner/ring storage, synchronization and growth.
"""


def enqueue_loading_destruction(owner, payload, *, lock, unlock, grow):
    """Attempt insertion then increment uint32 staged even if insertion failed.

    owner contains ring and staged; ring has slots/count/tail/capacity. Growth
    receives (ring, uint32(capacity+1024), True), and its result is not checked.
    Header is re-read after growth. Return diagnostics are authored, not native
    return values. Normal-return serial behavior only; no exception recovery.
    """
    lock(owner)
    ring=owner['ring'];grew=False;inserted=False
    if ring['capacity']<=ring['count']:
        grew=True;grow(ring,(ring['capacity']+1024)&0xffffffff,True)
    if ring['capacity']>ring['count']:
        ring['slots'][ring['tail']]=payload
        ring['count']+=1;ring['tail']=(ring['tail']+1)%ring['capacity'];inserted=True
    owner['staged']=(owner['staged']+1)&0xffffffff
    unlock(owner)
    return dict(inserted=inserted,growth_requested=grew)
