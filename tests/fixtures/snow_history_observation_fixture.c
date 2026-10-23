#include "snow_history_observation.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned char mem[0x10000];
static unsigned reads,fail_at,mutate;
static SnowHistoryProfile profile={0x1000,0x5000,0x6000,0x7000,0x7008};
static void put(size_t a,uint64_t v,size_t n) {for(size_t i=0;i<n;i++)mem[a+i]=(unsigned char)(v>>(8*i));}
static int read_mem(void *ctx,uint64_t a,void *out,size_t n) {
    (void)ctx;reads++;
    if(reads==fail_at || a>sizeof mem || n>sizeof mem-a)return 0;
    if(a==0x1000 && reads>1 && mutate==1)put(0x402c,2,4);
    if(a==0xa050 && mutate==2)put(0xa050,reads,8);
    memcpy(out,mem+a,n);return 1;
}
static void setup(void) {
    memset(mem,0,sizeof mem);reads=fail_at=mutate=0;
    put(0x1000,0x5000,8);put(0x5010,0x6000,8);put(0x1010,0x2000,8);put(0x10b0,0x4000,8);
    put(0x4030,1,4);put(0x4034,0x3dcccccd,4);
    put(0x23b0,0xc000,8);put(0x23ba,1,2);put(0xc000,0x3f000000,4);
    put(0x7000,0x8000,8);put(0x8188,0x9000,8);put(0x7008,0xb000,8);
    put(0xa050,100,8);put(0xb008,200,8);
    put(0x2010,9000,8);put(0x21b0,0x7fc01234,4); /* Preserve NaN payload as bits. */
}
static unsigned resolves;
static int resolver_mode;
static int resolve_action(void *ctx,void *actor,uint64_t *out) {
    assert(ctx==(void *)0x10 && actor==(void *)0x20);resolves++;
    *out=0x1000;
    if(resolver_mode==1 && resolves==2)*out=0x1100;
    if(resolver_mode==2)return 0;
    return 1;
}
static void check_trace_reader(void) {
    SnowHistoryTraceContext ctx={read_mem,0,resolve_action,(void *)0x10,0x5000,0x6000,0x7000,0x7008};
    SnowHistoryActionObservation out,zero={0};
    setup();resolves=0;resolver_mode=0;
    assert(snow_history_trace_read(&ctx,(void *)0x20,&out)==1 && resolves==2);
    assert(out.action==0x1000 && out.clock_ticks==100);
    setup();resolves=0;resolver_mode=1;
    assert(!snow_history_trace_read(&ctx,(void *)0x20,&out));
    assert(!memcmp(&out,&zero,sizeof out));
    setup();resolves=0;resolver_mode=2;
    assert(!snow_history_trace_read(&ctx,(void *)0x20,&out) && !reads && resolves==1);
    setup();resolves=0;resolver_mode=0;mutate=1;
    assert(!snow_history_trace_read(&ctx,(void *)0x20,&out) && resolves==1);
    setup();resolves=0;resolver_mode=0;mutate=2;
    assert(snow_history_trace_read(&ctx,(void *)0x20,&out)==1 && out.clock_ticks==reads);
    setup();resolves=0;resolver_mode=0;fail_at=1;
    assert(!snow_history_trace_read(&ctx,(void *)0x20,&out) && !memcmp(&out,&zero,sizeof out));
}
static unsigned original_calls;
static void original(void *actor,float elapsed,float derivative) {
    assert(actor==(void *)0x20 && elapsed==1 && derivative==2);
    original_calls++;put(0xa050,101,8);
}
static void snapshot(void *actor,SnowUpdateSnapshot *out) {(void)actor;out->valid=1;}
static uint64_t tick(void) {return 1;}
static void check_recorder_integration(void) {
    SnowUpdateTrace trace;SnowUpdateRecord row;
    SnowHistoryTraceContext ctx={read_mem,0,resolve_action,(void *)0x10,0x5000,0x6000,0x7000,0x7008};
    setup();resolves=0;resolver_mode=0;original_calls=0;
    assert(snow_trace_init(&trace,&row,1,original,snapshot,tick,tick));
    snow_trace_call_with_history(&trace,(void *)0x20,1,2,0,0,0,0,snow_history_trace_read,&ctx);
    snow_trace_close(&trace);assert(snow_trace_drained(&trace));
    assert(row.history_attempted && row.history_before_valid && row.history_after_valid);
    assert(row.history_before.clock_ticks==100 && row.history_after.clock_ticks==101);
    assert(resolves==4 && original_calls==1);
    snow_trace_call_with_history(&trace,(void *)0x20,1,2,0,0,0,0,snow_history_trace_read,&ctx);
    assert(resolves==4 && original_calls==2);
}
int main(void) {
    check_trace_reader();
    check_recorder_integration();
    SnowHistoryCapture c;setup();assert(snow_history_observe(read_mem,0,&profile,&c)==1);
    unsigned total=reads;assert(c.reads==reads && reads<=32 && c.bytes<=1024);
    assert(c.identities_match && c.dynamic_equal && c.samples[0].clock_ticks==100);
    assert(c.samples[0].history_times[0]==9000 && c.samples[0].history_b_bits[0]==0x7fc01234);
    for(unsigned i=1;i<=total;i++) {
        setup();fail_at=i;memset(&c,255,sizeof c);
        assert(snow_history_observe(read_mem,0,&profile,&c)==0);
        unsigned char zero[sizeof c.samples]={0};assert(!memcmp(c.samples,zero,sizeof zero));
        assert(!c.identities_match && !c.dynamic_equal);
    }
    setup();mutate=1;assert(snow_history_observe(read_mem,0,&profile,&c)==2);
    assert(!c.identities_match && c.dynamic_equal);
    setup();mutate=2;assert(snow_history_observe(read_mem,0,&profile,&c)==1);
    assert(c.identities_match && !c.dynamic_equal);
    setup();put(0x8188,0,8);assert(snow_history_observe(read_mem,0,&profile,&c)==1 && c.samples[0].clock_ticks==200);
    total=reads;
    for(unsigned i=1;i<=total;i++) {setup();put(0x8188,0,8);fail_at=i;assert(!snow_history_observe(read_mem,0,&profile,&c));}
    setup();put(0x7000,0,8);assert(snow_history_observe(read_mem,0,&profile,&c)==1 && c.samples[0].clock_ticks==200);
    setup();put(0x4028,1,4);put(0x2770,0xc000,8);put(0x277a,1,2);
    assert(snow_history_observe(read_mem,0,&profile,&c)==1 && c.samples[0].history==0x23d0);
    setup();put(0x4028,2,4);assert(!snow_history_observe(read_mem,0,&profile,&c));
    setup();put(0x8188,UINT64_MAX-3,8);assert(!snow_history_observe(read_mem,0,&profile,&c));
    setup();put(0x1000,7,8);assert(!snow_history_observe(read_mem,0,&profile,&c));assert(reads==1);
    setup();put(0x23ba,0,2);assert(!snow_history_observe(read_mem,0,&profile,&c));
    puts("PASS: bounded history capture, mutation, clock fallback, bits and failed reads");return 0;
}
