#include "snow_delegate_trace.h"
#include <string.h>
#define CLOSED (UINT64_C(1) << 63)

int snow_delegate_trace_init(SnowDelegateTrace *t, SnowDelegateRecord *r, size_t n,
    SnowDelegateOriginal original, SnowDelegateClock clock, SnowDelegateClock thread_id) {
    if (!t || !original || !clock || !thread_id || (n && !r)) return 0;
    t->records=r; t->capacity=n; t->original=original;
    t->clock=clock; t->thread_id=thread_id; t->observe=NULL;
    atomic_init(&t->gate,0); atomic_init(&t->used,0); atomic_init(&t->dropped,0);
    return 1;
}
uintptr_t snow_delegate_trace_call_from(SnowDelegateTrace *t, void *storage, void *receiver, uintptr_t caller) {
    uint_fast64_t gate=atomic_load(&t->gate);
    for (;;) {
        if ((gate&CLOSED) || gate==CLOSED-1) return t->original(storage,receiver);
        if (atomic_compare_exchange_weak(&t->gate,&gate,gate+1)) break;
    }
    size_t slot=atomic_load(&t->used);
    while (slot<t->capacity && !atomic_compare_exchange_weak(&t->used,&slot,slot+1)) {}
    uintptr_t result;
    if (slot>=t->capacity) {
        atomic_fetch_add(&t->dropped,1);
        result=t->original(storage,receiver);
    } else {
        SnowDelegateRecord *r=&t->records[slot];
        memset(r,0,sizeof *r);
        r->caller=caller; r->function_storage=(uintptr_t)storage; r->receiver=(uintptr_t)receiver;
        r->thread=t->thread_id(); r->entry_tick=t->clock();
        if(t->observe)t->observe(storage,receiver,&r->before);
        result=t->original(storage,receiver);
        r->result=result;
        if(t->observe)t->observe(storage,receiver,&r->after);
        r->exit_tick=t->clock();
    }
    atomic_fetch_sub(&t->gate,1);
    return result;
}
uintptr_t snow_delegate_trace_call(SnowDelegateTrace *t, void *storage, void *receiver) {
    return snow_delegate_trace_call_from(t,storage,receiver,0);
}
void snow_delegate_trace_close(SnowDelegateTrace *t) { atomic_fetch_or(&t->gate,CLOSED); }
int snow_delegate_trace_drained(const SnowDelegateTrace *t) { return atomic_load(&t->gate)==CLOSED; }
int snow_delegate_trace_read(const SnowDelegateTrace *t,size_t index,void *out,size_t size) {
    if (!t || !out || size!=sizeof(SnowDelegateRecord) || !snow_delegate_trace_drained(t) ||
        index>=atomic_load(&t->used) || index>=t->capacity) return 0;
    memcpy(out,&t->records[index],sizeof(SnowDelegateRecord));
    return 1;
}
