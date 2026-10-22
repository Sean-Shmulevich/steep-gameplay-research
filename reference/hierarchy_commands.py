"""Recovered hierarchy-command consumption and seven-bit completion gate.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Hierarchy command execution boundary.
Resolved record targets are supplied; locks, callbacks and lifetime are external.
"""


def drain_hierarchy_commands(*, pending, deferred, record_targets, entity_bytes,
                             read_index, capacity, max_iterations=4096):
    """Plan a single drain without producer or callback mutation.

    record_targets is logical dequeue order, with None for invisible/absent
    targets. entity_bytes maps inspection tokens to the target byte. Native
    visibility uses holder status bit 31 here, without the TLS override.
    Queue-budget mismatch deliberately preserves cached-record processing.
    Iteration and input guards are authored inspection policy.
    """
    for value in (pending,deferred):
        if type(value) is not int or not 0<=value<2**32:
            raise ValueError('uint32 command counters required')
    if type(capacity) is not int or not 1<=capacity<2**31:
        raise ValueError('positive signed ring capacity required')
    if type(read_index) is not int or not 0<=read_index<capacity:
        raise ValueError('read index outside ring')
    if not isinstance(record_targets,(list,tuple)) or len(record_targets)>capacity:
        raise ValueError('logical records must fit supplied ring capacity')
    values=dict(entity_bytes)
    if any(type(value) is not int or not 0<=value<=255 for value in values.values()):
        raise ValueError('uint8 entity fields required')
    if any(token is not None and token not in values for token in record_targets):
        raise ValueError('each visible record needs a supplied entity byte')
    if type(max_iterations) is not int or max_iterations<0:
        raise ValueError('nonnegative inspection budget required')
    total=(pending+deferred)&0xffffffff
    budget=total if total<0x80000000 else 0
    if budget>max_iterations:raise ValueError('inspection iteration budget exceeded')
    events=[];reattach_targets=[];consumed=0;cached=None
    for _ in range(budget):
        events.append('enter')
        if consumed<len(record_targets):
            cached=record_targets[consumed];consumed+=1
            read_index=(read_index+1)%capacity
        events.extend(['leave','process'])
        if cached is not None:
            old=values[cached]
            values[cached]=(old&128)|((old-1)&127)
            if values[cached]&127==0:
                events.append('reattach');reattach_targets.append(cached)
    return dict(events=events,reattach_targets=reattach_targets,
                remaining=len(record_targets)-consumed,read_index=read_index,
                entity_bytes=values,pending=0,deferred=0)


def full_ring_submission(*, count, capacity, write_index, deferred):
    """Recovered full-ring branch shared by both hierarchy producers.

    Rejecting other branches is adapter policy. No record is published, yet
    deferred budget increments. Caller byte updates and lifetime are external.
    """
    if any(type(v) is not int for v in (count,capacity,write_index,deferred)):
        raise ValueError('integer ring state required')
    if not 1<=capacity<=count<2**31 or not 0<=write_index<capacity:
        raise ValueError('full signed-positive ring state required')
    if not 0<=deferred<2**32:raise ValueError('uint32 deferred count required')
    return dict(count=count,write_index=write_index,deferred=(deferred+1)&0xffffffff,
                record_published=False)


def initial_hierarchy_queue(*, object_allocation_succeeds=True,
                            ring_allocation_succeeds=True):
    """Recovered startup result with allocation/lock services supplied.

    A ring allocation failure still publishes the object with capacity zero.
    No allocation or native pointer is exposed by this inspection model.
    """
    if any(type(v) is not bool for v in (object_allocation_succeeds,ring_allocation_succeeds)):
        raise ValueError('boolean allocation outcomes required')
    result=dict(published=object_allocation_succeeds,events=['object_allocate'])
    if object_allocation_succeeds:
        result['events']+=['lock_init','ring_allocate']
        result.update(count=0,write_index=0,read_index=0,
            capacity=2048 if ring_allocation_succeeds else 0,pending=0,deferred=0,
            storage_present=ring_allocation_succeeds)
    return result


def hierarchy_publication_state(*, count, capacity, write_index, deferred):
    """Recovered publication bookkeeping with valid allocated ring storage.

    Models both capacity branches. Actual record copying/holder retention are
    established separately by the instruction receipt, not performed here.
    """
    if any(type(v) is not int for v in (count,capacity,write_index,deferred)):
        raise ValueError('integer ring state required')
    if not 0<=count<2**31 or not 1<=capacity<2**31 or not 0<=write_index<capacity:
        raise ValueError('nonnegative occupancy and positive ring capacity required')
    if not 0<=deferred<2**32:raise ValueError('uint32 deferred count required')
    published=count<capacity
    return dict(count=count+int(published),
                write_index=(write_index+1)%capacity if published else write_index,
                deferred=(deferred+1)&0xffffffff,record_published=published)


def hierarchy_submission_byte(before, descriptor_valid):
    """Recovered post-producer update, after the producer returns/unlocks.

    Low seven bits increment with wrap. High bit is replaced, not retained:
    it is set exactly when the supplied descriptor validity is false.
    """
    if type(before) is not int or not 0<=before<=255:
        raise ValueError('uint8 entity byte required')
    if type(descriptor_valid) is not bool:
        raise ValueError('boolean descriptor validity required')
    return ((before+1)&127)|(0 if descriptor_valid else 128)


def hierarchy_transform_route(flags, descriptor_valid):
    """Recovered caller branch only; no native submission or transform mutation.

    Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Caller can bypass hierarchy queue.
    Validity is supplied. Route names and argument validation are authored.
    """
    if type(flags) is not int or not 0 <= flags <= 255:
        raise ValueError('uint8 flags required')
    if type(descriptor_valid) is not bool:
        raise ValueError('boolean descriptor validity required')
    if not descriptor_valid or flags & 4:
        return 'direct_dispatch'
    return 'queued' if flags & 1 else 'compose_then_dispatch'
