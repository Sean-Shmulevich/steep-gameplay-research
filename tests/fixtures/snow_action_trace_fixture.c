#include "snow_action_trace.h"
#include <assert.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <string.h>
static SnowActionTrace trace;
static SnowActionRecord records[8];
static atomic_uint calls,entered,release_call;
static atomic_uint_fast64_t ticks;
static int mode;
static _Thread_local int nested;
static uint64_t clock_tick(void) {return atomic_fetch_add(&ticks,1);}
static uint64_t thread_id(void) {return 7;} /* Synthetic thread identity. */
static void original(void *p) {
    ++*(unsigned *)p;atomic_fetch_add(&calls,1);
    if(mode==1 && !nested) {nested=1;snow_action_trace_call(&trace,p);nested=0;}
    if(mode==2) {
        atomic_store(&entered,1);
        while(!atomic_load(&release_call))sched_yield();
    }
}
static void init(size_t n) {
    assert(snow_action_trace_init(&trace,records,n,original,clock_tick,thread_id));
    atomic_store(&calls,0);atomic_store(&ticks,0);
}
static void *worker(void *p) {snow_action_trace_call(&trace,p);return NULL;}
static unsigned sample_calls;
static int sample_status[2];
static int sample(void *context,void *action,SnowActionSample *out) {
    assert(context==&trace);memset(out,0xa5,sizeof *out);
    out->vector_bits[0]=*(unsigned *)action;
    return sample_status[sample_calls++%2];
}
static void sample_checks(void) {
    unsigned value=0;SnowActionSample zero={0};mode=0;
    for(unsigned mask=0;mask<4;mask++) {
        init(1);sample_calls=0;sample_status[0]=mask&1?1:0;sample_status[1]=mask&2?1:2;
        snow_action_trace_call_observed(&trace,&value,sample,&trace);
        assert(records[0].sample_attempted && sample_calls==2);
        assert(records[0].before_valid==(unsigned)(sample_status[0]==1));
        assert(records[0].after_valid==(unsigned)(sample_status[1]==1));
        if(records[0].before_valid)assert(records[0].before.vector_bits[0]==value-1);
        else assert(!memcmp(&records[0].before,&zero,sizeof zero));
        if(records[0].after_valid)assert(records[0].after.vector_bits[0]==value);
        else assert(!memcmp(&records[0].after,&zero,sizeof zero));
        snow_action_trace_call_observed(&trace,&value,sample,&trace);
        snow_action_trace_close(&trace);
        snow_action_trace_call_observed(&trace,&value,sample,&trace);
        assert(sample_calls==2 && atomic_load(&calls)==3);
    }
}
int main(void) {
    unsigned value=0;SnowActionRecord out,unchanged;
    memset(&unchanged,0xa5,sizeof unchanged);out=unchanged;
    assert(!snow_action_trace_init(NULL,records,1,original,clock_tick,thread_id));
    init(2);mode=1;snow_action_trace_call(&trace,&value);
    assert(value==2 && atomic_load(&calls)==2);
    assert(!snow_action_trace_read(&trace,0,&out,sizeof out));
    assert(!memcmp(&out,&unchanged,sizeof out));
    snow_action_trace_close(&trace);assert(snow_action_trace_drained(&trace));
    assert(records[0].entry_tick==0 && records[0].exit_tick==3);
    assert(records[1].entry_tick==1 && records[1].exit_tick==2);
    assert(records[0].action==(uintptr_t)&value && records[0].thread==7);
    for(size_t n=0;n<sizeof out;n++)assert(!snow_action_trace_read(&trace,0,&out,n));
    assert(!memcmp(&out,&unchanged,sizeof out));
    assert(snow_action_trace_read(&trace,0,&out,sizeof out));
    assert(!snow_action_trace_read(&trace,2,&out,sizeof out));
    mode=0;snow_action_trace_call(&trace,&value);
    assert(value==3 && atomic_load(&ticks)==4);
    init(0);snow_action_trace_call(&trace,&value);
    assert(atomic_load(&trace.dropped)==1 && atomic_load(&calls)==1 && !atomic_load(&ticks));
    snow_action_trace_close(&trace);
    init(1);mode=2;atomic_store(&entered,0);atomic_store(&release_call,0);
    pthread_t thread;assert(!pthread_create(&thread,NULL,worker,&value));
    while(!atomic_load(&entered))sched_yield();
    snow_action_trace_close(&trace);assert(!snow_action_trace_drained(&trace));
    assert(!snow_action_trace_read(&trace,0,&out,sizeof out));
    atomic_store(&release_call,1);assert(!pthread_join(thread,NULL));
    assert(snow_action_trace_drained(&trace));
    assert(snow_action_trace_read(&trace,0,&out,sizeof out));
    assert(out.exit_tick>out.entry_tick);
    init(8);mode=0;
    pthread_t racers[16];unsigned values[16]={0};
    for(unsigned i=0;i<16;i++)assert(!pthread_create(&racers[i],NULL,worker,&values[i]));
    for(unsigned i=0;i<16;i++) {assert(!pthread_join(racers[i],NULL));assert(values[i]==1);}
    snow_action_trace_close(&trace);
    assert(snow_action_trace_drained(&trace) && atomic_load(&calls)==16);
    assert(atomic_load(&trace.used)==8 && atomic_load(&trace.dropped)==8);
    for(unsigned i=0;i<8;i++) {
        assert(snow_action_trace_read(&trace,i,&out,sizeof out));
        assert(out.exit_tick>out.entry_tick);
        for(unsigned j=0;j<i;j++)assert(records[j].action!=out.action);
    }
    sample_checks();
    puts("PASS: action events, nested order, overflow, late forwarding, close/drain and sized reads");
}
