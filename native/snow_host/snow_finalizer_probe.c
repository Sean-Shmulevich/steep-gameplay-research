#define WIN32_LEAN_AND_MEAN
#define SNOW_FINALIZER_PROBE_BUILD
#include <windows.h>
#include <string.h>
#include "snow_finalizer_probe.h"
static SnowFinalizerBinding binding;
static SnowDelegateTrace trace;
static SnowDelegateRecord records[1024];
static volatile LONG ready;
static SRWLOCK control=SRWLOCK_INIT;
static int attempted,protection_known;
static DWORD protection;
static void *volatile *slot;
static int read_at(uint64_t at,void *out,size_t n) {
    SIZE_T got=0;
    return ReadProcessMemory(GetCurrentProcess(),(void *)(uintptr_t)at,out,n,&got)&&got==n;
}
static uint64_t ticks(void) { LARGE_INTEGER q;QueryPerformanceCounter(&q);return q.QuadPart; }
static uint64_t thread_id(void) { return GetCurrentThreadId(); }
static uintptr_t forward(void *unused,void *job) {
    (void)unused;return ((SnowFinalizerOriginal)(uintptr_t)binding.original)(job);
}
static __attribute__((noinline)) uintptr_t dispatch(void *job) {
    if((uintptr_t)job!=binding.owner+0x218)return forward(NULL,job);
    return snow_delegate_trace_call_from(&trace,NULL,job,
        (uintptr_t)__builtin_extract_return_addr(__builtin_return_address(0)));
}
static int identity(void) {
    uint64_t owner,table,again;
    return read_at(binding.owner_global,&owner,8)&&owner==binding.owner&&
        read_at(owner+0x218,&table,8)&&table==binding.job_table&&
        read_at(binding.owner_global,&again,8)&&again==owner;
}
static int binding_valid(void) {
    uint64_t target;
    return identity()&&read_at(binding.job_table+0x70,&target,8)&&
        (target==binding.original||target==(uintptr_t)&dispatch);
}
static void observe(void *unused,void *job,SnowDelegateJobState *out) {
    (void)unused;uint32_t c[6];uint8_t usage,selector;SnowDelegateJobState s={0};
    if((uintptr_t)job!=binding.owner+0x218 || !binding_valid() ||
       !read_at((uintptr_t)job+0x4c,c,sizeof c) ||
       !read_at((uintptr_t)job+0x194,&usage,1) ||
       !read_at(binding.owner+0x5a,&selector,1) || !binding_valid())return;
    s.executions=c[0];memcpy(&s.outstanding,&c[1],4);s.state=c[2];
    s.started=c[3];s.requested=c[4];s.holds=c[5];s.usage=usage;s.selector=selector;
    s.valid=1;*out=s;
}
static int module_at(uint64_t at,int executable,HMODULE *module) {
    MEMORY_BASIC_INFORMATION m;
    if(!VirtualQuery((void *)(uintptr_t)at,&m,sizeof m)||m.State!=MEM_COMMIT||m.Type!=MEM_IMAGE||
       (m.Protect&(PAGE_GUARD|PAGE_NOACCESS)))return 0;
    if(executable && m.Protect!=PAGE_EXECUTE && m.Protect!=PAGE_EXECUTE_READ &&
       m.Protect!=PAGE_EXECUTE_READWRITE && m.Protect!=PAGE_EXECUTE_WRITECOPY)return 0;
    return GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
        (LPCSTR)(uintptr_t)at,module);
}
uint32_t SnowFinalizerProbe_ABIVersion(void) { return 1; }
size_t SnowFinalizerProbe_RecordSize(void) { return sizeof(SnowDelegateRecord); }
int SnowFinalizerProbe_Configure(const SnowFinalizerBinding *b) {
    int ok=0;HMODULE image,other,pinned;uint64_t target;MEMORY_BASIC_INFORMATION m;
    AcquireSRWLockExclusive(&control);
    if(!b||ready)goto done;
    InterlockedExchange(&ready,1);binding=*b;
    if(binding.owner<0x10000 || binding.owner>UINT64_C(0x7ffffffffff0)-0x3d0 ||
       binding.job_table>UINT64_C(0x7ffffffffff0)-0x78 || ((binding.job_table+0x70)&7) ||
       !module_at(binding.original,1,&image)||!module_at(binding.job_table+0x70,0,&other)||image!=other||
       !module_at(binding.owner_global,0,&other)||image!=other||
       !VirtualQuery((void *)(uintptr_t)(binding.job_table+0x70),&m,sizeof m)||
       (m.Protect!=PAGE_READONLY&&m.Protect!=PAGE_READWRITE&&m.Protect!=PAGE_WRITECOPY)||
       binding.job_table+0x78>(uintptr_t)m.BaseAddress+m.RegionSize||
       !identity()||!read_at(binding.job_table+0x70,&target,8)||target!=binding.original||
       !GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
          (LPCSTR)(uintptr_t)&dispatch,&pinned)||
       !GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
          (LPCSTR)(uintptr_t)binding.original,&pinned)||
       !snow_delegate_trace_init(&trace,records,1024,forward,ticks,thread_id)) {
        InterlockedExchange(&ready,-1);goto done;
    }
    trace.observe=observe;slot=(void *volatile *)(uintptr_t)(binding.job_table+0x70);
    InterlockedExchange(&ready,2);ok=1;
done:ReleaseSRWLockExclusive(&control);return ok;
}
static int restore_locked(void) {
    DWORD old,ignored;void *seen;
    if(!protection_known)return 1;
    /* Slot belongs to pinned image: restore remains possible after owner loss. */
    if(!VirtualProtect((void *)slot,8,PAGE_READWRITE,&old))return -1;
    seen=InterlockedCompareExchangePointer(slot,(void *)(uintptr_t)binding.original,(void *)(uintptr_t)&dispatch);
    int owned=seen==(void *)(uintptr_t)&dispatch||seen==(void *)(uintptr_t)binding.original;
    if(!VirtualProtect((void *)slot,8,protection,&ignored))return -1;
    return owned;
}
int SnowFinalizerProbe_Install(void) {
    int ok=0;uint64_t target;DWORD ignored;MEMORY_BASIC_INFORMATION m;
    AcquireSRWLockExclusive(&control);
    if(ready!=2||attempted||(atomic_load(&trace.gate)&(UINT64_C(1)<<63)))goto done;
    attempted=1;
    if(!identity()||!read_at(binding.job_table+0x70,&target,8)||target!=binding.original||
       !VirtualQuery((void *)slot,&m,sizeof m)||m.State!=MEM_COMMIT||m.Type!=MEM_IMAGE||
       (m.Protect!=PAGE_READONLY&&m.Protect!=PAGE_READWRITE&&m.Protect!=PAGE_WRITECOPY))goto done;
    if(!VirtualProtect((void *)slot,8,PAGE_READWRITE,&protection)){ok=-1;goto done;}
    protection_known=1;
    void *seen=InterlockedCompareExchangePointer(slot,(void *)(uintptr_t)&dispatch,(void *)(uintptr_t)binding.original);
    ok=seen==(void *)(uintptr_t)binding.original;
    if(!VirtualProtect((void *)slot,8,protection,&ignored)){restore_locked();ok=-1;}
done:ReleaseSRWLockExclusive(&control);return ok;
}
int SnowFinalizerProbe_Restore(void) {
    AcquireSRWLockExclusive(&control);
    int result=ready==2?restore_locked():0;
    ReleaseSRWLockExclusive(&control);return result;
}
int SnowFinalizerProbe_Close(size_t *used,size_t *dropped) {
    if(InterlockedCompareExchange(&ready,2,2)!=2)return 0;
    snow_delegate_trace_close(&trace);
    if(!snow_delegate_trace_drained(&trace))return 0;
    if(used)*used=atomic_load(&trace.used);
    if(dropped)*dropped=atomic_load(&trace.dropped);
    return 1;
}
int SnowFinalizerProbe_Read(size_t i,void *out,size_t size) {
    return InterlockedCompareExchange(&ready,2,2)==2&&snow_delegate_trace_read(&trace,i,out,size);
}
