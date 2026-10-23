"""Runnable serial composition; synthetic storage and services, no native mod API."""
import json
from engine.command_record_cleanup import cleanup_record
from engine.holder_release_queue import release_holder_to_queue
from engine.holder_ring_resize import resize_holder_ring


def run_probe(*, capacity=4, count=4, head=3, alias=False, allocation_fails=False,
              mode=1, thread_kind=0):
    events=[]; receipts=[]
    old=[{'name':f'prior-{i}'} for i in range(capacity)]
    ring=dict(slots=old,storage=old if capacity else None,capacity=capacity,
              count=count,head=head,tail=(head+count)%capacity if capacity else 0,owns_storage=True)
    registry=dict(mode=mode,ring=ring)
    h1=dict(name='holder-10',status=2 if alias else 1,payload='payload-10')
    h2=h1 if alias else dict(name='holder-08',status=1,payload='payload-08')
    record=dict(associated=dict(count=1),invoker='not-executed',holder_10=h1,holder_08=h2)
    def allocate(size):
        events.append(['allocate',size])
        return None if allocation_fails else [None]*(size//8)
    def copy(dst,src,start,n):
        if dst is None:
            raise ValueError('null copy destination; native outcome unresolved')
        dst[:n]=[src[(start+i)%len(src)] for i in range(n)]
    def grow(r,size,preserve):
        try:resize_holder_ring(r,size,preserve,allocate=allocate,copy=copy,
                              free=lambda _:events.append(['free']))
        finally:r['slots']=r['storage']
    def release(h):
        receipt=release_holder_to_queue(h,registry,global_suppress=False,
            lock=lambda _:events.append(['lock']),unlock=lambda _:events.append(['unlock']),
            grow=grow,cleanup=lambda _,x:events.append(['cleanup',x['name']]),
            classify_thread=lambda:thread_kind,
            post_unlock=lambda _:events.append(['post_unlock']))
        receipts.append(dict(holder=h['name'],**receipt))
    cleanup_record(record,destroy_associated=lambda _:events.append(['destroy_associated']),release_holder=release)
    queued=[ring['slots'][(ring['head']+i)%ring['capacity']]['name'] for i in range(ring['count'])]
    return dict(evidence='Serial recovered composition with synthetic storage and external services',
        events=events,receipts=receipts,queued=queued,
        header={k:ring[k] for k in ('capacity','count','head','tail','owns_storage')},
        statuses=[h1['status'],h2['status']],associated_detached=record['associated'] is None,
        invoker_cleared=record['invoker'] is None,disposal_completion_proved=False)


if __name__=='__main__':
    print(json.dumps(run_probe(),indent=2))
