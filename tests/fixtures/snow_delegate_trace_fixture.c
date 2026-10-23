#include "snow_delegate_trace.h"
#include <assert.h>
#include <pthread.h>
#include <sched.h>
#include <string.h>
static atomic_int entered,release_call,calls;
static atomic_uint_fast64_t ticks;
static SnowDelegateTrace trace;
static int storage, receiver, other;
static uint64_t clock_tick(void) { return atomic_fetch_add(&ticks,1); }
static uint64_t thread_id(void) { return 7; }
static uintptr_t original(void *s,void *r) {
    assert(s==&storage); atomic_fetch_add(&calls,1);
    if(r==&receiver) {
        atomic_store(&entered,1);
        while(!atomic_load(&release_call)) sched_yield();
    }
    return (uintptr_t)r ^ UINT64_C(0xfedcba9876543210);
}
static void *worker(void *ignored) {
    (void)ignored;
    assert(snow_delegate_trace_call_from(&trace,&storage,&receiver,UINT64_C(0x123456789abcdef0))==((uintptr_t)&receiver ^ UINT64_C(0xfedcba9876543210)));
    return NULL;
}
int main(void) {
    SnowDelegateRecord records[1],copy,unchanged;
    pthread_t thread;
    memset(&copy,0xa5,sizeof copy);unchanged=copy;
    assert(snow_delegate_trace_init(&trace,records,1,original,clock_tick,thread_id));
    assert(!snow_delegate_trace_read(&trace,0,&copy,sizeof copy));
    assert(!memcmp(&copy,&unchanged,sizeof copy));
    assert(!pthread_create(&thread,NULL,worker,NULL));
    while(!atomic_load(&entered)) sched_yield();
    snow_delegate_trace_close(&trace);
    assert(!snow_delegate_trace_drained(&trace));
    /* A cached late call still forwards, but cannot reserve/write a record. */
    assert(snow_delegate_trace_call(&trace,&storage,&other)==((uintptr_t)&other ^ UINT64_C(0xfedcba9876543210)));
    assert(!snow_delegate_trace_read(&trace,0,&copy,sizeof copy));
    atomic_store(&release_call,1);assert(!pthread_join(thread,NULL));
    assert(snow_delegate_trace_drained(&trace));
    assert(atomic_load(&calls)==2 && atomic_load(&trace.used)==1);
    assert(snow_delegate_trace_read(&trace,0,&copy,sizeof copy));
    assert(copy.function_storage==(uintptr_t)&storage && copy.receiver==(uintptr_t)&receiver);
    assert(copy.result==((uintptr_t)&receiver ^ UINT64_C(0xfedcba9876543210)));
    assert(copy.exit_tick>copy.entry_tick && copy.thread==7);
    assert(copy.caller==UINT64_C(0x123456789abcdef0));
    assert(!snow_delegate_trace_read(&trace,1,&copy,sizeof copy));
    assert(!snow_delegate_trace_read(&trace,0,&copy,sizeof copy-1));
    SnowDelegateTrace zero;
    assert(snow_delegate_trace_init(&zero,NULL,0,original,clock_tick,thread_id));
    assert(snow_delegate_trace_call(&zero,&storage,&other)==((uintptr_t)&other ^ UINT64_C(0xfedcba9876543210)));
    assert(atomic_load(&zero.dropped)==1 && atomic_load(&zero.used)==0);
    snow_delegate_trace_close(&zero);assert(snow_delegate_trace_drained(&zero));
    assert(!snow_delegate_trace_read(&zero,0,&copy,sizeof copy));
    assert(!snow_delegate_trace_init(NULL,NULL,0,original,clock_tick,thread_id));
    return 0;
}
