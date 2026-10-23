#include "snow_command_observation.h"
#include <assert.h>
#include <string.h>
static uint64_t ticks;
static uint64_t clock_tick(void){return ++ticks;}
static uint64_t thread_id(void){return 71;}
/* Synthetic dispatcher applies the recovered low-two-bit context mask. */
static uintptr_t dispatch(SnowCommandDescriptor *record){
    return ((SnowDelegateOriginal)record->invoker)(record,(void *)(record->context&~(uintptr_t)3));
}
int main(void){
    SnowCommandObservation owner;
    SnowCommandDescriptor source,copy;
    SnowDelegateRecord records[2],r;
    assert(!snow_command_observation_init(&owner,&source,0,records,2,clock_tick,thread_id));
    assert(snow_command_observation_init(&owner,&source,42,records,2,clock_tick,thread_id));
    copy=source;
    memset(&source,0,sizeof source);
    copy.context|=3;
    assert(dispatch(&copy)==42);
    assert(!snow_delegate_trace_read(&owner.trace,0,&r,sizeof r));
    assert(dispatch(&copy)==42); /* Same descriptor can be delivered again. */
    assert(dispatch(&copy)==42); /* Full recorder still returns normally. */
    assert(atomic_load(&owner.trace.used)==2);
    assert(atomic_load(&owner.trace.dropped)==1);
    snow_delegate_trace_close(&owner.trace);
    assert(snow_delegate_trace_drained(&owner.trace));
    assert(snow_delegate_trace_read(&owner.trace,0,&r,sizeof r));
    assert(r.receiver==(uintptr_t)&owner && r.function_storage==(uintptr_t)&copy);
    assert(r.result==42 && r.thread==71 && r.entry_tick<r.exit_tick && r.caller);
    assert(snow_delegate_trace_read(&owner.trace,1,&r,sizeof r));
    assert(r.result==42 && r.thread==71);
    assert(dispatch(&copy)==42); /* Cached call after close still safe while retained. */
    assert(atomic_load(&owner.trace.used)==2 && atomic_load(&owner.trace.dropped)==1);
    assert(!snow_delegate_trace_read(&owner.trace,2,&r,sizeof r));
    return 0;
}
