#include "snow_markup_trace.h"
#include <string.h>
#define CLOSED (UINT64_C(1) << 63)

int snow_markup_trace_init(SnowMarkupTrace *t, SnowMarkupRecord *r, size_t n,
    SnowMarkupOriginal original, SnowMarkupClock clock, SnowMarkupClock thread_id, uintptr_t owner) {
    if (!t || !original || !clock || !thread_id || (n && !r)) return 0;
    t->records=r; t->capacity=n; t->original=original;
    t->clock=clock; t->thread_id=thread_id; t->owner=owner;
    atomic_init(&t->gate,0); atomic_init(&t->used,0); atomic_init(&t->dropped,0);
    return 1;
}
uintptr_t snow_markup_trace_call(SnowMarkupTrace *t, void *storage, void *receiver, uint32_t id, uint8_t value, uint32_t extra, uintptr_t caller) {
    uint_fast64_t gate=atomic_load(&t->gate);
    for (;;) {
        if ((gate&CLOSED) || gate==CLOSED-1) return t->original(storage,receiver,id,value,extra);
        if (atomic_compare_exchange_weak(&t->gate,&gate,gate+1)) break;
    }
    size_t slot=atomic_load(&t->used);
    while (slot<t->capacity && !atomic_compare_exchange_weak(&t->used,&slot,slot+1)) {}
    uintptr_t result;
    if (slot>=t->capacity) {
        atomic_fetch_add(&t->dropped,1);
        result=t->original(storage,receiver,id,value,extra);
    } else {
        SnowMarkupRecord *r=&t->records[slot];
        memset(r,0,sizeof *r);
        r->caller=caller; r->descriptor=(uintptr_t)storage; r->receiver=(uintptr_t)receiver;
        r->owner=t->owner; r->markup_id=id; r->value=value; r->extra=extra;
        r->thread=t->thread_id(); r->entry_tick=t->clock();
        result=t->original(storage,receiver,id,value,extra);
        r->result=result;
        r->exit_tick=t->clock();
    }
    atomic_fetch_sub(&t->gate,1);
    return result;
}
void snow_markup_trace_close(SnowMarkupTrace *t) { atomic_fetch_or(&t->gate,CLOSED); }
int snow_markup_trace_drained(const SnowMarkupTrace *t) { return atomic_load(&t->gate)==CLOSED; }
int snow_markup_trace_read(const SnowMarkupTrace *t,size_t index,void *out,size_t size) {
    if (!t || !out || size!=sizeof(SnowMarkupRecord) || !snow_markup_trace_drained(t) ||
        index>=atomic_load(&t->used) || index>=t->capacity) return 0;
    memcpy(out,&t->records[index],sizeof(SnowMarkupRecord));
    return 1;
}
