#include "snow_update_trace.h"
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <sched.h>
#include <string.h>
static SnowUpdateTrace trace;
static SnowUpdateRecord rows[128];
static atomic_uint calls, reads;
static atomic_uint_fast64_t ticks;
static int mode;
static atomic_int entered, release_call;
static _Thread_local int nested;
static uint64_t clock_tick(void) { return atomic_fetch_add(&ticks,1); }
static uint64_t thread_id(void) { return 1; } /* Fixture only; not a native TID. */
static void read_state(void *actor, SnowUpdateSnapshot *s) {
    atomic_fetch_add(&reads,1); s->valid=1; s->runtime=(uintptr_t)actor;
    s->linear[0][0]=(float)*(int *)actor; s->angular[0][1]=7;
}
static void original(void *actor,float elapsed,float derivative) {
    assert(elapsed==0.125f && derivative==0.5f);
    atomic_fetch_add(&calls,1); ++*(int *)actor;
    if (mode==1 && !nested) {
        nested=1; snow_trace_call(&trace,actor,elapsed,derivative); nested=0;
    }
    if (mode==3) {
        atomic_store(&entered,1);
        while (!atomic_load(&release_call)) sched_yield();
    }
    if (mode==2) {
        snow_trace_close(&trace);
        assert(!snow_trace_drained(&trace));
    }
}
static void init(size_t capacity) {
    assert(snow_trace_init(&trace,rows,capacity,original,read_state,clock_tick,thread_id));
    atomic_store(&calls,0); atomic_store(&reads,0); atomic_store(&ticks,0);
}
static void *worker(void *unused) {
    (void)unused; int actor=0;
    for(int i=0;i<200;i++) snow_trace_call(&trace,&actor,0.125f,0.5f);
    assert(actor==200); return NULL;
}
static unsigned observations;
static int observe_entry(void *ctx,SnowEntryAttribution *out,SnowBatchFrame *frame) {
    ++observations;
    memset(frame,0xa5,sizeof *frame);
    memset(out,0xa5,sizeof *out); /* failure must discard partially written data */
    return *(int *)ctx;
}
static void check_attribution(void) {
    int actor=0, success=1; SnowEntryAttribution zero={0};
    mode=0; init(2); observations=0;
    snow_trace_call_attributed(&trace,&actor,.125f,.5f,observe_entry,&success);
    success=0;
    snow_trace_call_attributed(&trace,&actor,.125f,.5f,observe_entry,&success);
    /* Overflow and closed capture forward without optional observation. */
    snow_trace_call_attributed(&trace,&actor,.125f,.5f,observe_entry,&success);
    snow_trace_close(&trace);
    snow_trace_call_attributed(&trace,&actor,.125f,.5f,observe_entry,&success);
    assert(snow_trace_drained(&trace) && actor==4 && atomic_load(&calls)==4);
    assert(observations==2 && atomic_load(&trace.dropped)==1);
    assert(rows[0].attribution_attempted==1 && rows[0].attribution_valid==1);
    assert(rows[1].attribution_attempted==1 && rows[1].attribution_valid==0);
    assert(!memcmp(&rows[1].attribution,&zero,sizeof zero));
    SnowBatchFrame blank={0};
    assert(!rows[0].frame_valid && !memcmp(&rows[0].frame,&blank,sizeof blank));
    assert(!rows[1].frame_valid && !memcmp(&rows[1].frame,&blank,sizeof blank));
    init(1);success=3;
    snow_trace_call_attributed(&trace,&actor,.125f,.5f,observe_entry,&success);snow_trace_close(&trace);
    assert(rows[0].attribution_valid && rows[0].frame_valid);
    init(1); snow_trace_call(&trace,&actor,.125f,.5f);snow_trace_close(&trace);
    assert(!rows[0].attribution_attempted && !rows[0].attribution_valid);
}
typedef struct { int before,after; unsigned calls; } MotionFixture;
static int observe_motion(void *ctx,void *actor,SnowMotionObservation *out) {
    MotionFixture *m=ctx;
    memset(out,0xa5,sizeof *out);
    out->nonzero_counts[0]=(unsigned)*(int *)actor;
    return m->calls++==0 ? m->before : m->after;
}
static void check_motion(void) {
    SnowMotionObservation blank={0};
    for(int before=0;before<3;before++) for(int after=0;after<3;after++) {
        int actor=0,status=3; MotionFixture m={before,after,0};
        mode=0; init(1);
        snow_trace_call_observed(&trace,&actor,.125f,.5f,observe_entry,&status,observe_motion,&m);
        snow_trace_call_observed(&trace,&actor,.125f,.5f,observe_entry,&status,observe_motion,&m);
        snow_trace_close(&trace);
        snow_trace_call_observed(&trace,&actor,.125f,.5f,observe_entry,&status,observe_motion,&m);
        assert(snow_trace_drained(&trace) && actor==3 && atomic_load(&calls)==3);
        assert(m.calls==2 && rows[0].motion_attempted);
        assert(rows[0].attribution_valid && rows[0].frame_valid);
        assert(rows[0].before.valid && rows[0].after.valid);
        assert(rows[0].motion_before_valid==(before==1));
        assert(rows[0].motion_after_valid==(after==1));
        if(before==1) assert(rows[0].motion_before.nonzero_counts[0]==0);
        else assert(!memcmp(&rows[0].motion_before,&blank,sizeof blank));
        if(after==1) assert(rows[0].motion_after.nonzero_counts[0]==1);
        else assert(!memcmp(&rows[0].motion_after,&blank,sizeof blank));
    }
    int actor=0,status=0; MotionFixture m={1,1,0}; init(1);
    snow_trace_call_observed(&trace,&actor,.125f,.5f,observe_entry,&status,observe_motion,&m);
    snow_trace_close(&trace);
    assert(!rows[0].attribution_valid && !rows[0].frame_valid);
    assert(rows[0].motion_before_valid && rows[0].motion_after_valid);
    init(1);snow_trace_call(&trace,&actor,.125f,.5f);snow_trace_close(&trace);
    assert(!rows[0].motion_attempted && !rows[0].motion_before_valid && !rows[0].motion_after_valid);
}
static int observe_history(void *ctx,void *actor,SnowHistoryActionObservation *out) {
    MotionFixture *m=ctx;
    memset(out,0xa5,sizeof *out);
    out->clock_ticks=(unsigned)*(int *)actor;
    out->action=0x1234;
    return m->calls++==0 ? m->before : m->after;
}
static void check_history(void) {
    SnowHistoryActionObservation blank={0};
    for(int before=0;before<3;before++) for(int after=0;after<3;after++) {
        int actor=0,status=0; MotionFixture h={before,after,0},m={1,1,0};
        mode=0;init(1);
        snow_trace_call_with_history(&trace,&actor,.125f,.5f,observe_entry,&status,
            observe_motion,&m,observe_history,&h);
        snow_trace_call_with_history(&trace,&actor,.125f,.5f,NULL,NULL,
            NULL,NULL,observe_history,&h);
        snow_trace_close(&trace);
        snow_trace_call_with_history(&trace,&actor,.125f,.5f,NULL,NULL,
            NULL,NULL,observe_history,&h);
        assert(snow_trace_drained(&trace) && actor==3 && h.calls==2 && m.calls==2);
        assert(atomic_load(&calls)==3 && atomic_load(&trace.dropped)==1);
        assert(rows[0].history_attempted && !rows[0].attribution_valid);
        assert(rows[0].motion_before_valid && rows[0].motion_after_valid);
        assert(rows[0].history_before_valid==(before==1));
        assert(rows[0].history_after_valid==(after==1));
        if(before==1) assert(rows[0].history_before.clock_ticks==0);
        else assert(!memcmp(&rows[0].history_before,&blank,sizeof blank));
        if(after==1) assert(rows[0].history_after.clock_ticks==1);
        else assert(!memcmp(&rows[0].history_after,&blank,sizeof blank));
    }
    int actor=0;init(1);
    snow_trace_call(&trace,&actor,.125f,.5f);snow_trace_close(&trace);
    assert(!rows[0].history_attempted && !rows[0].history_before_valid && !rows[0].history_after_valid);
    assert(!memcmp(&rows[0].history_before,&blank,sizeof blank));
}
static void check_sized_read(void) {
    int actor=0;SnowUpdateRecord copy,sentinel;
    memset(&sentinel,0xa5,sizeof sentinel);copy=sentinel;
    mode=0;init(1);
    assert(!snow_trace_read_record(&trace,0,&copy,sizeof copy));
    snow_trace_call(&trace,&actor,.125f,.5f);
    assert(!snow_trace_read_record(&trace,0,&copy,sizeof copy));
    snow_trace_close(&trace);
    for(size_t size=0;size<sizeof copy;size++) {
        assert(!snow_trace_read_record(&trace,0,&copy,size));
        assert(!memcmp(&copy,&sentinel,sizeof copy));
    }
    assert(!snow_trace_read_record(&trace,0,&copy,sizeof copy+1));
    assert(!snow_trace_read_record(&trace,1,&copy,sizeof copy));
    assert(!snow_trace_read_record(&trace,0,NULL,sizeof copy));
    assert(!memcmp(&copy,&sentinel,sizeof copy));
    assert(snow_trace_read_record(&trace,0,&copy,sizeof copy));
    assert(!memcmp(&copy,&rows[0],sizeof copy));
}
int main(void) {
    check_attribution();
    check_motion();
    check_history();
    check_sized_read();
    int actor=0;
    assert(!snow_trace_init(NULL,rows,1,original,read_state,clock_tick,thread_id));
    mode=1; init(128);
    snow_trace_call(&trace,&actor,0.125f,0.5f);
    assert(!snow_trace_drained(&trace)); snow_trace_close(&trace);
    assert(snow_trace_drained(&trace) && atomic_load(&trace.used)==2);
    assert(rows[0].before.linear[0][0]==0 && rows[0].after.linear[0][0]==2);
    assert(rows[1].before.linear[0][0]==1 && rows[1].after.linear[0][0]==2);
    assert(rows[0].entry_tick<rows[1].entry_tick && rows[1].exit_tick<rows[0].exit_tick);
    /* Reinitialization below is fixture-only, with no retained/cached callers. */
    mode=2; init(128); actor=0;
    snow_trace_call(&trace,&actor,0.125f,0.5f);
    assert(snow_trace_drained(&trace));
    SnowUpdateRecord saved=rows[0]; mode=0;
    snow_trace_call(&trace,&actor,0.125f,0.5f);
    assert(actor==2 && atomic_load(&reads)==2 && atomic_load(&trace.used)==1);
    assert(memcmp(&saved,&rows[0],sizeof saved)==0);
    mode=0; init(128); pthread_t threads[4];
    for(int i=0;i<4;i++) assert(!pthread_create(&threads[i],NULL,worker,NULL));
    for(int i=0;i<4;i++) assert(!pthread_join(threads[i],NULL));
    snow_trace_close(&trace); assert(snow_trace_drained(&trace));
    assert(atomic_load(&calls)==800 && atomic_load(&trace.used)==128);
    assert(atomic_load(&trace.dropped)==672 && atomic_load(&reads)==256);
    for(int i=0;i<128;i++) {
        assert(rows[i].before.valid && rows[i].after.valid);
        assert(rows[i].after.linear[0][0]==rows[i].before.linear[0][0]+1);
        assert(rows[i].before.angular[0][1]==rows[i].after.angular[0][1]);
        assert(rows[i].entry_tick<rows[i].exit_tick);
    }
    mode=3; init(128); atomic_store(&entered,0); atomic_store(&release_call,0);
    assert(!pthread_create(&threads[0],NULL,worker,NULL));
    while (!atomic_load(&entered)) sched_yield();
    snow_trace_close(&trace); assert(!snow_trace_drained(&trace));
    atomic_store(&release_call,1); assert(!pthread_join(threads[0],NULL));
    assert(snow_trace_drained(&trace) && atomic_load(&calls)==200);
    assert(atomic_load(&trace.used)==1 && atomic_load(&reads)==2);
    mode=0; init(0); actor=0; snow_trace_call(&trace,&actor,0.125f,0.5f); snow_trace_close(&trace);
    assert(actor==1 && atomic_load(&trace.dropped)==1 && !atomic_load(&reads));
    puts("PASS: nested calls, close during call, late forwarding, concurrent capacity, zero capacity");
    return 0;
}
