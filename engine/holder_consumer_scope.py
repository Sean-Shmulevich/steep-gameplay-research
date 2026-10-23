"""Serial outer retirement-consumer protocol; raw coordination fields stay unnamed.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Consumer guard and worker handoff.
Synchronization and signaling are supplied; this is not a native barrier.
"""


def run_holder_consumer(registry, coordination, worker, *, lock, unlock,
                        process_one, signal):
    """Execute normal-return guard, dynamic queue loop and worker handoff.

    registry: processing, ring.count. coordination: active, word, limit.
    worker: pending, published, semaphore (uint32). process_one must consume or
    otherwise progress the queue; callbacks can add work. No iteration cap is
    invented. Exceptions do not synthesize native unlock/unwind semantics.
    """
    lock('global_1d8');lock('registry_b8')
    if registry['processing'] != 0:
        unlock('global_1d8');unlock('registry_b8')
        return dict(entered=False,iterations=0,transferred=0,signaled=False)
    registry['processing']=1;coordination['active']=1
    lock('coordination')
    coordination['word']=(coordination['word']&0xff800000)|0x800000
    coordination['limit']=0x3fffffff
    iterations=0
    while registry['ring']['count']>0:
        process_one(registry);iterations+=1
    pending=worker['pending'];worker['pending']=0
    signaled=False
    if pending:
        worker['published']=(worker['published']+pending)&0xffffffff
        old=worker['semaphore']
        signed=old-(1<<32) if old & (1<<31) else old
        worker['semaphore']=((signed+1) if signed<1 else 1)&0xffffffff
        if signed<0:
            signal();signaled=True
    registry['processing']=0;coordination['active']=0
    unlock('coordination');unlock('global_1d8');unlock('registry_b8')
    return dict(entered=True,iterations=iterations,transferred=pending,signaled=signaled)
