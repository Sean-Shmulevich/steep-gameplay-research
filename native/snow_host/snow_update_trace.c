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
    snow_trace_call_attributed(t,actor,elapsed,derivative,NULL,NULL);
}
void snow_trace_call_attributed(SnowUpdateTrace *t,void *actor,float elapsed,float derivative,
                                SnowUpdateEntryRead observe,void *context) {
    snow_trace_call_observed(t,actor,elapsed,derivative,observe,context,NULL,NULL);
}
void snow_trace_call_observed(SnowUpdateTrace *t,void *actor,float elapsed,float derivative,
                             SnowUpdateEntryRead observe,void *context,
                             SnowUpdateMotionRead motion,void *motion_context) {
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
        if(observe) {
            r->attribution_attempted=1;
            int status=observe(context,&r->attribution,&r->frame);
            r->attribution_valid=status==1 || status==3;
            r->frame_valid=status==3;
            if(!r->frame_valid) memset(&r->frame,0,sizeof r->frame);
            if(!r->attribution_valid) memset(&r->attribution,0,sizeof r->attribution);
        }
        t->read(actor,&r->before);
        if(motion) {
            r->motion_attempted=1;
            r->motion_before_valid=motion(motion_context,actor,&r->motion_before)==1;
            if(!r->motion_before_valid) memset(&r->motion_before,0,sizeof r->motion_before);
        }
        t->original(actor,elapsed,derivative);
        if(motion) {
            r->motion_after_valid=motion(motion_context,actor,&r->motion_after)==1;
            if(!r->motion_after_valid) memset(&r->motion_after,0,sizeof r->motion_after);
        }
        t->read(actor,&r->after);
        r->exit_tick=t->clock();
    }
    atomic_fetch_sub(&t->gate,1);
}
void snow_trace_close(SnowUpdateTrace *t) { atomic_fetch_or(&t->gate,CLOSED); }
int snow_trace_drained(const SnowUpdateTrace *t) { return atomic_load(&t->gate)==CLOSED; }
