#define WIN32_LEAN_AND_MEAN
#define SNOW_UPDATE_PROBE_BUILD
#include <windows.h>
#include "snow_update_probe.h"
#define CAPACITY 4096
static SnowUpdateTrace trace;
static SnowUpdateRecord records[CAPACITY];
static SnowUpdateBinding binding;
static LONG ready;
static int read_memory(void *ctx,uint64_t at,void *dst,size_t n) {
    (void)ctx; SIZE_T got=0;
    return ReadProcessMemory(GetCurrentProcess(),(const void *)(uintptr_t)at,dst,n,&got) && got==n;
}
static void snapshot(void *actor,SnowUpdateSnapshot *out) {
    (void)actor; snow_update_snapshot(read_memory,NULL,&binding,out);
}
static uint64_t ticks(void) { LARGE_INTEGER q; QueryPerformanceCounter(&q); return (uint64_t)q.QuadPart; }
static uint64_t thread_id(void) { return GetCurrentThreadId(); }
int SnowProbe_Configure(const SnowUpdateBinding *b,SnowUpdateOriginal original) {
    HMODULE module; SnowUpdateSnapshot check;
    if(!b || !original) return 0;
    if(InterlockedCompareExchange(&ready,1,0)!=0) return 0;
    binding=*b;
    if(!snow_update_snapshot(read_memory,NULL,&binding,&check) ||
       !GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
                          (LPCSTR)(uintptr_t)&SnowProbe_Configure,&module) ||
       !snow_trace_init(&trace,records,CAPACITY,original,snapshot,ticks,thread_id)) {
        InterlockedExchange(&ready,-1); return 0;
    }
    InterlockedExchange(&ready,2); return 1;
}
void SnowProbe_Dispatch(void *actor,float elapsed,float derivative) {
    /* Publishing before Configure succeeds violates the ABI. Never install until ready. */
    if(InterlockedCompareExchange(&ready,2,2)!=2) return;
    if((uint64_t)(uintptr_t)actor!=binding.actor) {
        trace.original(actor,elapsed,derivative); return;
    }
    snow_trace_call(&trace,actor,elapsed,derivative);
}
int SnowProbe_Close(size_t *used,size_t *dropped) {
    if(InterlockedCompareExchange(&ready,2,2)!=2) return 0;
    snow_trace_close(&trace);
    if(!snow_trace_drained(&trace)) return 0;
    if(used) *used=atomic_load(&trace.used);
    if(dropped) *dropped=atomic_load(&trace.dropped);
    return 1;
}
int SnowProbe_ReadRecord(size_t i,SnowUpdateRecord *out) {
    if(!out || InterlockedCompareExchange(&ready,2,2)!=2 || !snow_trace_drained(&trace) ||
       i>=atomic_load(&trace.used)) return 0;
    *out=records[i]; return 1;
}
