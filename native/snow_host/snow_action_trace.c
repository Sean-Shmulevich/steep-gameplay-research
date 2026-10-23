#include "snow_action_trace.h"
#include <string.h>
#define CLOSED (UINT64_C(1)<<63)
int snow_action_trace_init(SnowActionTrace *t,SnowActionRecord *r,size_t n,
                          SnowActionOriginal original,SnowActionClock clock,SnowActionClock thread) {
    if(!t || (n && !r) || !original || !clock || !thread)return 0;
    t->records=r;t->capacity=n;t->original=original;t->clock=clock;t->thread_id=thread;
    atomic_init(&t->gate,0);atomic_init(&t->used,0);atomic_init(&t->dropped,0);
    return 1;
}
void snow_action_trace_call(SnowActionTrace *t,void *action) {
    uint_fast64_t g=atomic_load(&t->gate);
    for(;;) {
        if((g&CLOSED) || g==CLOSED-1) {t->original(action);return;}
        if(atomic_compare_exchange_weak(&t->gate,&g,g+1))break;
    }
    size_t slot=atomic_load(&t->used);
    while(slot<t->capacity && !atomic_compare_exchange_weak(&t->used,&slot,slot+1)){}
    if(slot>=t->capacity) {
        atomic_fetch_add(&t->dropped,1);
        t->original(action);
    } else {
        SnowActionRecord *r=&t->records[slot];
        memset(r,0,sizeof *r);r->action=(uintptr_t)action;
        r->thread=t->thread_id();r->entry_tick=t->clock();
        t->original(action);
        r->exit_tick=t->clock();
    }
    atomic_fetch_sub(&t->gate,1);
}
void snow_action_trace_close(SnowActionTrace *t) {atomic_fetch_or(&t->gate,CLOSED);}
int snow_action_trace_drained(const SnowActionTrace *t) {return atomic_load(&t->gate)==CLOSED;}
int snow_action_trace_read(const SnowActionTrace *t,size_t i,void *out,size_t n) {
    if(!t || !out || n!=sizeof(SnowActionRecord) || !snow_action_trace_drained(t) ||
       i>=atomic_load(&t->used) || i>=t->capacity)return 0;
    memcpy(out,&t->records[i],sizeof(SnowActionRecord));return 1;
}
