#include "snow_markup_update_trace.h"
#include <assert.h>
#include <pthread.h>
#include <sched.h>
#include <string.h>
#include <stdio.h>
static SnowMarkupUpdateTrace *active;
static atomic_int calls,reads,entered,release_call;
static atomic_uint_fast64_t ticks;
static _Thread_local int phase;
static uint64_t tick(void) {return atomic_fetch_add(&ticks,1);}
static uint64_t thread_id(void) {return 7;}
static void invoke(uintptr_t id);
static void original(void *component,float value) {
    uint32_t bits;memcpy(&bits,&value,sizeof bits);assert(bits==(uint32_t)(uintptr_t)component);
    uintptr_t id=(uintptr_t)component;atomic_fetch_add(&calls,1);
    if(id==999) {atomic_store(&entered,1);while(!atomic_load(&release_call))sched_yield();}
    if(id==900)invoke(901);
    phase=1;
}
static int observe(void *context,void *component,SnowMarkupUpdateSnapshot *s) {
    assert(context==(void *)42);atomic_fetch_add(&reads,1);
    memset(s,0,sizeof *s);s->component=(uintptr_t)component;s->record_count=(uint16_t)!phase;
    if((uintptr_t)component==13 || ((uintptr_t)component==14 && !phase)) {
        memset(s,0xff,sizeof *s);return 2; /* not accepted, not merely nonzero */
    }
    return 1;
}
static void invoke(uintptr_t id) {
    uint32_t bits=(uint32_t)id;float argument;memcpy(&argument,&bits,sizeof argument);
    phase=0;snow_markup_update_trace_call(active,(void *)id,argument,123);
}
static void *bulk(void *unused) {(void)unused;for(uintptr_t i=0;i<100;i++)invoke(i);return NULL;}
static void *blocked(void *unused) {(void)unused;invoke(999);return NULL;}
static void init(SnowMarkupUpdateTrace *t,SnowMarkupUpdateRecord *r,size_t count) {
    assert(snow_markup_update_trace_init(t,r,count,original,tick,thread_id,observe,(void *)42));active=t;
}
static void zero_sample(const SnowMarkupUpdateSnapshot *s) {
    SnowMarkupUpdateSnapshot zero;memset(&zero,0,sizeof zero);assert(!memcmp(s,&zero,sizeof zero));
}
int main(void) {
    SnowMarkupUpdateTrace concurrent,race,recursive,invalid,zero;
    SnowMarkupUpdateRecord records[17],copy,untouched;pthread_t threads[8];
    assert(!snow_markup_update_trace_init(NULL,records,17,original,tick,thread_id,observe,NULL));
    assert(!snow_markup_update_trace_init(&concurrent,NULL,17,original,tick,thread_id,observe,NULL));
    init(&concurrent,records,17);memset(&copy,0xa5,sizeof copy);untouched=copy;
    assert(!snow_markup_update_trace_read(active,0,&copy,sizeof copy));assert(!memcmp(&copy,&untouched,sizeof copy));
    for(int i=0;i<8;i++)assert(!pthread_create(&threads[i],NULL,bulk,NULL));
    for(int i=0;i<8;i++)assert(!pthread_join(threads[i],NULL));
    assert(atomic_load(&calls)==800 && atomic_load(&reads)==34);
    assert(atomic_load(&active->used)==17 && atomic_load(&active->dropped)==783);
    snow_markup_update_trace_close(active);assert(snow_markup_update_trace_drained(active));
    for(size_t i=0;i<17;i++) {
        assert(snow_markup_update_trace_read(active,i,&copy,sizeof copy));
        assert(copy.argument_bits==(uint32_t)copy.component);
        assert(copy.caller==123 && copy.thread==7 && copy.exit_tick>copy.entry_tick);
        if(copy.before_valid)assert(copy.before.record_count==1);else zero_sample(&copy.before);
        if(copy.after_valid)assert(copy.after.record_count==0);else zero_sample(&copy.after);
    }
    assert(!snow_markup_update_trace_read(active,17,&copy,sizeof copy));
    assert(!snow_markup_update_trace_read(active,0,&copy,sizeof copy-1));
    invoke(88);assert(atomic_load(&calls)==801 && atomic_load(&reads)==34);

    init(&invalid,records,2);invoke(13);invoke(14);snow_markup_update_trace_close(active);
    assert(snow_markup_update_trace_read(active,0,&copy,sizeof copy));
    assert(!copy.before_valid && !copy.after_valid);zero_sample(&copy.before);zero_sample(&copy.after);
    assert(snow_markup_update_trace_read(active,1,&copy,sizeof copy));
    assert(!copy.before_valid && copy.after_valid);zero_sample(&copy.before);

    init(&recursive,records,2);invoke(900);snow_markup_update_trace_close(active);
    assert(atomic_load(&active->used)==2 && snow_markup_update_trace_drained(active));
    assert(records[0].component==900 && records[1].component==901);
    assert(records[0].entry_tick<records[1].entry_tick && records[0].exit_tick>records[1].exit_tick);

    init(&race,records,1);assert(!pthread_create(&threads[0],NULL,blocked,NULL));
    while(!atomic_load(&entered))sched_yield();
    snow_markup_update_trace_close(active);assert(!snow_markup_update_trace_drained(active));
    assert(!snow_markup_update_trace_read(active,0,&copy,sizeof copy));
    int before_reads=atomic_load(&reads);invoke(77);assert(atomic_load(&reads)==before_reads);
    atomic_store(&release_call,1);assert(!pthread_join(threads[0],NULL));
    assert(snow_markup_update_trace_drained(active));
    assert(snow_markup_update_trace_read(active,0,&copy,sizeof copy));assert(copy.component==999);
    assert(atomic_load(&active->used)==1 && atomic_load(&active->dropped)==0);

    init(&zero,NULL,0);before_reads=atomic_load(&reads);invoke(8);
    assert(atomic_load(&active->dropped)==1 && atomic_load(&reads)==before_reads);
    snow_markup_update_trace_close(active);assert(snow_markup_update_trace_drained(active));
    init(&invalid,records,4);
    invoke(0);invoke(0x80000000);invoke(0x7f800000);invoke(0x7fc00001);
    snow_markup_update_trace_close(active);
    for(size_t i=0;i<4;i++)assert(records[i].argument_bits==(uint32_t)records[i].component);
    puts("markup update trace passed: concurrency, overflow, recursion, invalid samples, close-in-flight, late forwarding");
    return 0;
}
