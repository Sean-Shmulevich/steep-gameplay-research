"""Serial captured-budget resource preparation; external dispatch is supplied.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Captured resource preparation budget.
Uses existing deferred-entry decision semantics. No native locks or lifetime pin.
"""
from .animation_resource_index import capture_resource_count, deferred_entry_decision


def prepare_resource_queue(registry, *, lock, unlock, dispatch_current):
    """Exchange published budget once, then pop exactly that many valid triples.

    Registry has published and ring; ring has slots/count/head/capacity. Each
    triple has key, queued_record and holder; queued_record is not used. Holder
    has token, status and payload. Callbacks may publish further work; it stays
    pending for another call. Budget exceeding available entries raises an
    authored boundary error rather than inventing native empty-queue recovery.
    """
    lock(registry)
    captured=capture_resource_count(registry['published'])['captured']
    registry['published']=0
    consumed=0;dispatched=0
    while consumed<captured:
        ring=registry['ring']
        if ring['count']<=0:
            raise ValueError('captured budget exceeds available triples; native invalid access boundary')
        slot=ring['head'];ring['head']=(slot+1)%ring['capacity'];ring['count']-=1
        triple=ring['slots'][slot];holder=triple['holder']
        decision=deferred_entry_decision(triple['key'],holder['token'],holder['status'],
                                         has_current_record=holder['payload'] is not None)
        if decision['action']!='skip':
            holder['status']=decision['flags']
            if holder['payload'] is not None:
                dispatch_current(holder['payload']);dispatched+=1
        consumed+=1
    unlock(registry)
    return dict(captured=captured,consumed=consumed,dispatched=dispatched)
