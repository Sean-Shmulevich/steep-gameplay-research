#include "snow_animation_queue_trace.h"
#include <string.h>
#define CLOSED (UINT64_C(1)<<63)
int snow_animation_queue_trace_init(SnowAnimationQueueTrace *t,SnowAnimationQueueRecord *r,size_t n,
    SnowAnimationQueueOriginal original,SnowAnimationQueueClock clock,SnowAnimationQueueClock thread,
    SnowAnimationQueueRead read,void *context) {
    if(!t || (n && !r) || !original || !clock || !thread || !read)return 0;
    t->records=r;t->capacity=n;t->original=original;t->clock=clock;t->thread_id=thread;
    t->read=read;t->read_context=context;
    atomic_init(&t->gate,0);atomic_init(&t->used,0);atomic_init(&t->dropped,0);return 1;
}
uintptr_t snow_animation_queue_trace_call(SnowAnimationQueueTrace *t,void *component,uintptr_t caller) {
    uint_fast64_t g=atomic_load(&t->gate);
    for(;;) {
        if((g&CLOSED) || g==CLOSED-1)return t->original(component);
        if(atomic_compare_exchange_weak(&t->gate,&g,g+1))break;
    }
    size_t slot=atomic_load(&t->used);
    while(slot<t->capacity && !atomic_compare_exchange_weak(&t->used,&slot,slot+1)){}
    uintptr_t result;
    if(slot>=t->capacity) {
        atomic_fetch_add(&t->dropped,1);result=t->original(component);
    } else {
        SnowAnimationQueueRecord *r=&t->records[slot];memset(r,0,sizeof *r);
        r->component=(uintptr_t)component;r->caller=caller;
        r->thread=t->thread_id();r->entry_tick=t->clock();
        r->before_valid=t->read(t->read_context,component,&r->before)==1;
        if(!r->before_valid)memset(&r->before,0,sizeof r->before);
        result=t->original(component);r->result=result;
        r->after_valid=t->read(t->read_context,component,&r->after)==1;
        if(!r->after_valid)memset(&r->after,0,sizeof r->after);
        r->exit_tick=t->clock();
    }
    atomic_fetch_sub(&t->gate,1);return result;
}
void snow_animation_queue_trace_close(SnowAnimationQueueTrace *t) {atomic_fetch_or(&t->gate,CLOSED);}
int snow_animation_queue_trace_drained(const SnowAnimationQueueTrace *t) {return atomic_load(&t->gate)==CLOSED;}
int snow_animation_queue_trace_read(const SnowAnimationQueueTrace *t,size_t i,void *out,size_t n) {
    if(!t || !out || n!=sizeof(SnowAnimationQueueRecord) || !snow_animation_queue_trace_drained(t) ||
       i>=atomic_load(&t->used) || i>=t->capacity)return 0;
    memcpy(out,&t->records[i],sizeof(SnowAnimationQueueRecord));return 1;
}
