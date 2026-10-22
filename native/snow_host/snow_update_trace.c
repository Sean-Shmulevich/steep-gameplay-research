#include "snow_update_trace.h"
#include <string.h>
#define CLOSED (UINT64_C(1) << 63)
int snow_trace_init(SnowUpdateTrace *t, SnowUpdateRecord *r, size_t n,
                    SnowUpdateOriginal original, SnowUpdateRead read,
                    SnowUpdateClock clock, SnowUpdateClock thread_id) {
    if (!t || !original || !read || !clock || !thread_id || (n && !r)) return 0;
    t->records=r; t->capacity=n; t->original=original; t->read=read;
    t->clock=clock; t->thread_id=thread_id;
    atomic_init(&t->gate,0); atomic_init(&t->used,0); atomic_init(&t->dropped,0);
    return 1;
}
void snow_trace_call(SnowUpdateTrace *t, void *actor, float elapsed, float derivative) {
    uint_fast64_t g=atomic_load(&t->gate);
    for (;;) {
        if (g & CLOSED) { t->original(actor,elapsed,derivative); return; }
        /* Refuse capture on counter saturation, but preserve the original call. */
        if (g == CLOSED-1) { t->original(actor,elapsed,derivative); return; }
        if (atomic_compare_exchange_weak(&t->gate,&g,g+1)) break;
    }
    size_t slot=atomic_load(&t->used);
    while (slot<t->capacity && !atomic_compare_exchange_weak(&t->used,&slot,slot+1)) {}
    if (slot>=t->capacity) {
        atomic_fetch_add(&t->dropped,1);
        t->original(actor,elapsed,derivative);
    } else {
        SnowUpdateRecord *r=&t->records[slot];
        memset(r,0,sizeof *r);
        r->actor=(uintptr_t)actor; r->elapsed=elapsed; r->derivative=derivative;
        r->thread=t->thread_id(); r->entry_tick=t->clock();
        t->read(actor,&r->before);
        t->original(actor,elapsed,derivative);
        t->read(actor,&r->after);
        r->exit_tick=t->clock();
    }
    atomic_fetch_sub(&t->gate,1);
}
void snow_trace_close(SnowUpdateTrace *t) { atomic_fetch_or(&t->gate,CLOSED); }
int snow_trace_drained(const SnowUpdateTrace *t) { return atomic_load(&t->gate)==CLOSED; }
