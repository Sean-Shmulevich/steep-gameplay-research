#include "snow_markup_update_trace.h"
#include <string.h>
_Static_assert(sizeof(float)==sizeof(uint32_t),"32-bit float required");
#define CLOSED (UINT64_C(1)<<63)
int snow_markup_update_trace_init(SnowMarkupUpdateTrace *t,SnowMarkupUpdateRecord *r,size_t n,
    SnowMarkupUpdateOriginal original,SnowMarkupUpdateClock clock,SnowMarkupUpdateClock thread,
    SnowMarkupUpdateRead read,void *context) {
    if(!t || (n && !r) || !original || !clock || !thread || !read)return 0;
    t->records=r;t->capacity=n;t->original=original;t->clock=clock;t->thread_id=thread;
    t->read=read;t->read_context=context;
    atomic_init(&t->gate,0);atomic_init(&t->used,0);atomic_init(&t->dropped,0);return 1;
}
void snow_markup_update_trace_call(SnowMarkupUpdateTrace *t,void *component,float argument,uintptr_t caller) {
    uint_fast64_t g=atomic_load(&t->gate);
    for(;;) {
        if((g&CLOSED) || g==CLOSED-1) {t->original(component,argument);return;}
        if(atomic_compare_exchange_weak(&t->gate,&g,g+1))break;
    }
    size_t slot=atomic_load(&t->used);
    while(slot<t->capacity && !atomic_compare_exchange_weak(&t->used,&slot,slot+1)){}
    if(slot>=t->capacity) {
        atomic_fetch_add(&t->dropped,1);t->original(component,argument);
    } else {
        SnowMarkupUpdateRecord *r=&t->records[slot];memset(r,0,sizeof *r);
        r->component=(uintptr_t)component;r->caller=caller;
        memcpy(&r->argument_bits,&argument,sizeof argument);
        r->thread=t->thread_id();r->entry_tick=t->clock();
        r->before_valid=t->read(t->read_context,component,&r->before)==1;
        if(!r->before_valid)memset(&r->before,0,sizeof r->before);
        t->original(component,argument);
        r->after_valid=t->read(t->read_context,component,&r->after)==1;
        if(!r->after_valid)memset(&r->after,0,sizeof r->after);
        r->exit_tick=t->clock();
    }
    atomic_fetch_sub(&t->gate,1);
}
void snow_markup_update_trace_close(SnowMarkupUpdateTrace *t) {atomic_fetch_or(&t->gate,CLOSED);}
int snow_markup_update_trace_drained(const SnowMarkupUpdateTrace *t) {return atomic_load(&t->gate)==CLOSED;}
int snow_markup_update_trace_read(const SnowMarkupUpdateTrace *t,size_t i,void *out,size_t n) {
    if(!t || !out || n!=sizeof(SnowMarkupUpdateRecord) || !snow_markup_update_trace_drained(t) ||
       i>=atomic_load(&t->used) || i>=t->capacity)return 0;
    memcpy(out,&t->records[i],sizeof(SnowMarkupUpdateRecord));return 1;
}
