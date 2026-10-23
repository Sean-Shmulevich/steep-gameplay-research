#define WIN32_LEAN_AND_MEAN
#define SNOW_DELEGATE_PROBE_BUILD
#include <windows.h>
#include <string.h>
#include "snow_delegate_probe.h"
#define CAPACITY 1024
#define CLOSED (UINT64_C(1)<<63)
static SnowDelegateBinding binding;
static uint32_t job_offset=0x218,descriptor_offset=0x3b0;
static SnowDelegateTrace trace;
static SnowDelegateRecord records[CAPACITY];
static volatile LONG ready;
static SRWLOCK control=SRWLOCK_INIT;
static int attempted,installed;
static volatile LONG request_state; /* 0 unused, 1 armed, 2 running, 3 returned */
static SnowDelegateRequestObservation request_observation;
static uint64_t manager_global;
static void *volatile *slot;
static int read_at(uint64_t at,void *dst,size_t n) {
    SIZE_T got=0;
    return ReadProcessMemory(GetCurrentProcess(),(void *)(uintptr_t)at,dst,n,&got) && got==n;
}
static uint64_t clock_tick(void) { LARGE_INTEGER q; QueryPerformanceCounter(&q);return (uint64_t)q.QuadPart; }
static uint64_t thread_id(void) { return GetCurrentThreadId(); }
static __attribute__((noinline)) uintptr_t dispatch(void *storage,void *receiver) {
    /* Install is the only supported publisher, after successful configure. */
    uintptr_t caller=(uintptr_t)__builtin_extract_return_addr(__builtin_return_address(0));
    int claimed=InterlockedCompareExchange(&request_state,2,1)==1;
    if(claimed) {
        request_observation.entry_tick=clock_tick();
        request_observation.thread=thread_id();request_observation.caller=caller;
        request_observation.receiver=(uintptr_t)receiver;request_observation.storage=(uintptr_t)storage;
        request_observation.valid_before=read_at(manager_global,&request_observation.manager_before,8);
    }
    uintptr_t result=snow_delegate_trace_call_from(&trace,storage,receiver,caller);
    if(claimed) {
        request_observation.valid_after=read_at(manager_global,&request_observation.manager_after,8);
        request_observation.result=result;request_observation.exit_tick=clock_tick();
        InterlockedExchange(&request_state,3);
    }
    return result;
}
static int image_at(uint64_t at,int executable,HMODULE *module) {
    MEMORY_BASIC_INFORMATION m;
    if(!at || !VirtualQuery((void *)(uintptr_t)at,&m,sizeof m) ||
       m.State!=MEM_COMMIT || m.Type!=MEM_IMAGE || (m.Protect&(PAGE_GUARD|PAGE_NOACCESS))) return 0;
    if(executable && m.Protect!=PAGE_EXECUTE && m.Protect!=PAGE_EXECUTE_READ &&
       m.Protect!=PAGE_EXECUTE_READWRITE && m.Protect!=PAGE_EXECUTE_WRITECOPY) return 0;
    return GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                             (LPCSTR)(uintptr_t)at,module);
}
static int qualify(uint64_t *invoker) {
    uint64_t owner,table,method,d[4],again;MEMORY_BASIC_INFORMATION m;
    uint64_t address=binding.owner+descriptor_offset+24;
    if(binding.owner<0x10000 || binding.owner>UINT64_C(0x7ffffffffff0)-(descriptor_offset+32) ||
       (address&7) || (binding.context&~UINT64_C(3))!=binding.owner ||
       !read_at(binding.owner_global,&owner,8) || owner!=binding.owner ||
       !read_at(owner+job_offset,&table,8) || table!=binding.job_table ||
       !read_at(table+0x40,&method,8) || method!=binding.dispatch_method ||
       !read_at(owner+descriptor_offset,d,sizeof d) || d[0]!=binding.function ||
       d[1]!=binding.auxiliary || d[2]!=binding.context ||
       !VirtualQuery((void *)(uintptr_t)address,&m,sizeof m) || m.Type!=MEM_PRIVATE ||
       m.State!=MEM_COMMIT || m.Protect!=PAGE_READWRITE ||
       address+8>(uintptr_t)m.BaseAddress+m.RegionSize ||
       !read_at(binding.owner_global,&again,8) || again!=owner) return 0;
    *invoker=d[3];return 1;
}
static void observe_job(void *storage,void *receiver,SnowDelegateJobState *out) {
    SnowDelegateJobState s={0};uint64_t invoker;
    uint32_t counters[6];uint8_t usage,selector;
    /* A cached wrapper can be called after restoration. Both our wrapper and
     * the original are acceptable; a third-party invoker is not qualified. */
    if((uintptr_t)storage!=binding.owner+descriptor_offset || (uintptr_t)receiver!=binding.owner ||
       !qualify(&invoker) || (invoker!=binding.invoker && invoker!=(uintptr_t)&dispatch) ||
       !read_at(binding.owner+job_offset+0x4c,counters,sizeof counters) ||
       !read_at(binding.owner+job_offset+0x194,&usage,1) ||
       !read_at(binding.owner+0x5a,&selector,1) ||
       !qualify(&invoker) || (invoker!=binding.invoker && invoker!=(uintptr_t)&dispatch)) return;
    s.executions=counters[0];memcpy(&s.outstanding,&counters[1],sizeof s.outstanding);
    s.state=counters[2];s.started=counters[3];s.requested=counters[4];s.holds=counters[5];
    s.usage=usage;s.selector=selector;s.valid=1;*out=s;
}
uint32_t SnowDelegateProbe_ABIVersion(void) { return 3; }
size_t SnowDelegateProbe_RecordSize(void) { return sizeof(SnowDelegateRecord); }
int SnowDelegateProbe_Configure(const SnowDelegateBinding *b) {
    return SnowDelegateProbe_ConfigureSite(b,SNOW_DELEGATE_GRAPHICS_MAIN);
}
int SnowDelegateProbe_ConfigureSite(const SnowDelegateBinding *b,SnowDelegateSite site) {
    int ok=0;uint64_t invoker;HMODULE module,other,pinned;
    AcquireSRWLockExclusive(&control);
    if(!b || ready || (site!=SNOW_DELEGATE_GRAPHICS_MAIN && site!=SNOW_DELEGATE_ENGINE_MAIN)) goto done;
    job_offset=site==SNOW_DELEGATE_GRAPHICS_MAIN?0x218:0x740;
    descriptor_offset=job_offset+0x198;
    InterlockedExchange(&ready,1);binding=*b;
    if(!image_at(binding.invoker,1,&module) || !image_at(binding.function,1,&other) || module!=other ||
       !image_at(binding.dispatch_method,1,&other) || module!=other ||
       !image_at(binding.job_table,0,&other) || module!=other ||
       !image_at(binding.owner_global,0,&other) || module!=other ||
       !qualify(&invoker) || invoker!=binding.invoker ||
       !GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
                          (LPCSTR)(uintptr_t)&dispatch,&pinned) ||
       !GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
                          (LPCSTR)(uintptr_t)binding.invoker,&pinned) ||
       !snow_delegate_trace_init(&trace,records,CAPACITY,
           (SnowDelegateOriginal)(uintptr_t)binding.invoker,clock_tick,thread_id)) {
        InterlockedExchange(&ready,-1);goto done;
    }
    trace.observe=observe_job;
    slot=(void *volatile *)(uintptr_t)(binding.owner+descriptor_offset+24);
    InterlockedExchange(&ready,2);ok=1;
done: ReleaseSRWLockExclusive(&control);return ok;
}
int SnowDelegateProbe_Install(void) {
    int ok=0;uint64_t seen;
    AcquireSRWLockExclusive(&control);
    if(ready!=2 || attempted || (atomic_load(&trace.gate)&CLOSED)) goto done;
    attempted=1;
    if(!qualify(&seen) || seen!=binding.invoker) goto done;
    void *previous=InterlockedCompareExchangePointer(slot,(void *)(uintptr_t)&dispatch,(void *)(uintptr_t)binding.invoker);
    installed=previous==(void *)(uintptr_t)binding.invoker;ok=installed;
done: ReleaseSRWLockExclusive(&control);return ok;
}
int SnowDelegateProbe_Restore(void) {
    int ok=0;uint64_t seen;
    AcquireSRWLockExclusive(&control);
    if(ready!=2) goto done;
    if(!installed) { ok=1;goto done; }
    if(!qualify(&seen)) goto done;
    if(seen==binding.invoker) { installed=0;ok=1;goto done; }
    if(seen!=(uint64_t)(uintptr_t)&dispatch) goto done;
    void *previous=InterlockedCompareExchangePointer(slot,(void *)(uintptr_t)binding.invoker,(void *)(uintptr_t)&dispatch);
    if(previous==(void *)(uintptr_t)&dispatch || previous==(void *)(uintptr_t)binding.invoker) { installed=0;ok=1; }
done: ReleaseSRWLockExclusive(&control);return ok;
}
int SnowDelegateProbe_Close(size_t *used,size_t *dropped) {
    if(InterlockedCompareExchange(&ready,2,2)!=2) return 0;
    snow_delegate_trace_close(&trace);
    if(!snow_delegate_trace_drained(&trace)) return 0;
    if(used)*used=atomic_load(&trace.used);
    if(dropped)*dropped=atomic_load(&trace.dropped);
    return 1;
}
int SnowDelegateProbe_Read(size_t i,void *out,size_t n) {
    if(InterlockedCompareExchange(&ready,2,2)!=2)return 0;
    return snow_delegate_trace_read(&trace,i,out,n);
}

int SnowDelegateProbe_ArmObservation(uint64_t id) {
    int ok=0;HMODULE module;
    AcquireSRWLockExclusive(&control);
    if(ready==2 && job_offset==0x740 && !attempted && !(atomic_load(&trace.gate)&CLOSED) && id && request_state==0 &&
       image_at(binding.function,1,&module)) {
        manager_global=(uintptr_t)module+0x312f3a8;
        request_observation.request_id=id;
        InterlockedExchange(&request_state,1);ok=1;
    }
    ReleaseSRWLockExclusive(&control);return ok;
}
int SnowDelegateProbe_ReadObservation(SnowDelegateRequestObservation *out) {
    if(!out || InterlockedCompareExchange(&request_state,3,3)!=3)return 0;
    *out=request_observation;return 1;
}
