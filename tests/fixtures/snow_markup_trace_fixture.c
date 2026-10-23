#include "snow_markup_trace.h"
#include <assert.h>
#include <pthread.h>
#include <sched.h>
#include <string.h>
static atomic_int calls, entered, release_call;
static atomic_uint_fast64_t ticks;
static int descriptor, receiver;
static SnowMarkupTrace storage_trace;
static SnowMarkupTrace *active=&storage_trace;
#define trace (*active)
static uint64_t tick(void) { return atomic_fetch_add(&ticks,1); }
static uint64_t tid(void) { return 7; }
static uintptr_t original(void *d, void *r, uint32_t id, uint8_t value, uint32_t extra) {
    assert(d==&descriptor && r==&receiver);
    assert(value==(uint8_t)id && extra==UINT32_MAX);
    atomic_fetch_add(&calls,1);
    if(id==999) {
        atomic_store(&entered,1);
        while(!atomic_load(&release_call)) sched_yield();
    }
    return UINT64_C(0xfedcba9876543210)^id;
}
static void invoke(uint32_t id) {
    assert(snow_markup_trace_call(&trace,&descriptor,&receiver,id,(uint8_t)id,
        UINT32_MAX,123)==(UINT64_C(0xfedcba9876543210)^id));
}
static void *bulk(void *ignored) {
    (void)ignored;
    for(uint32_t i=0;i<100;i++) invoke(i);
    return NULL;
}
static void *blocked(void *ignored) { (void)ignored;invoke(999);return NULL; }
int main(void) {
    SnowMarkupRecord records[17],copy,untouched;
    pthread_t threads[8];
    assert(!snow_markup_trace_init(NULL,records,17,original,tick,tid,42));
    assert(!snow_markup_trace_init(&trace,NULL,17,original,tick,tid,42));
    assert(!snow_markup_trace_init(&trace,records,17,NULL,tick,tid,42));
    assert(snow_markup_trace_init(&trace,records,17,original,tick,tid,42));
    memset(&copy,0xa5,sizeof copy); untouched=copy;
    assert(!snow_markup_trace_read(&trace,0,&copy,sizeof copy));
    assert(!memcmp(&copy,&untouched,sizeof copy));
    for(int i=0;i<8;i++) assert(!pthread_create(&threads[i],NULL,bulk,NULL));
    for(int i=0;i<8;i++) assert(!pthread_join(threads[i],NULL));
    assert(atomic_load(&calls)==800);
    assert(atomic_load(&trace.used)==17 && atomic_load(&trace.dropped)==783);
    assert(!snow_markup_trace_drained(&trace));
    snow_markup_trace_close(&trace);
    assert(snow_markup_trace_drained(&trace));
    for(size_t i=0;i<17;i++) {
        assert(snow_markup_trace_read(&trace,i,&copy,sizeof copy));
        assert(copy.descriptor==(uintptr_t)&descriptor && copy.receiver==(uintptr_t)&receiver);
        assert(copy.owner==42 && copy.caller==123 && copy.thread==7);
        assert(copy.value==(uint8_t)copy.markup_id && copy.extra==UINT32_MAX);
        assert(copy.result==(UINT64_C(0xfedcba9876543210)^copy.markup_id));
        assert(copy.exit_tick>copy.entry_tick);
    }
    assert(!snow_markup_trace_read(&trace,17,&copy,sizeof copy));
    assert(!snow_markup_trace_read(&trace,0,&copy,sizeof copy-1));
    invoke(255); /* Closed callers still forward without changing records. */
    assert(atomic_load(&calls)==801 && atomic_load(&trace.used)==17);
    assert(atomic_load(&trace.dropped)==783);

    /* A separate instance, never reopen a published recorder. */
    SnowMarkupTrace race;
    assert(snow_markup_trace_init(&race,records,1,original,tick,tid,43));
    /* Worker below uses trace; all previous workers have been joined. */
    active=&race;
    assert(!pthread_create(&threads[0],NULL,blocked,NULL));
    while(!atomic_load(&entered)) sched_yield();
    snow_markup_trace_close(&trace);
    assert(!snow_markup_trace_drained(&trace));
    assert(!snow_markup_trace_read(&trace,0,&copy,sizeof copy));
    invoke(254);
    atomic_store(&release_call,1);
    assert(!pthread_join(threads[0],NULL));
    assert(snow_markup_trace_drained(&trace));
    assert(snow_markup_trace_read(&trace,0,&copy,sizeof copy));
    assert(copy.markup_id==999 && copy.value==(uint8_t)999 && copy.owner==43);
    assert(atomic_load(&trace.used)==1 && atomic_load(&trace.dropped)==0);

    SnowMarkupTrace zero;
    assert(snow_markup_trace_init(&zero,NULL,0,original,tick,tid,0));
    snow_markup_trace_call(&zero,&descriptor,&receiver,0,0,UINT32_MAX,0);
    assert(atomic_load(&zero.dropped)==1 && atomic_load(&zero.used)==0);
    snow_markup_trace_close(&zero);
    assert(snow_markup_trace_drained(&zero));
    assert(!snow_markup_trace_read(&zero,0,&copy,sizeof copy));
    return 0;
}
