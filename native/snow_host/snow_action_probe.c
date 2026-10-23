#define WIN32_LEAN_AND_MEAN
#define SNOW_ACTION_PROBE_BUILD
#include <windows.h>
#include "snow_action_probe.h"
#define CAPACITY 8192
static SnowActionTrace trace;
static SnowActionRecord records[CAPACITY];
static LONG ready;
static uint64_t slot_address;
static SnowActionRead observe;
static void *observe_context;
static int read_memory(void *ctx,uint64_t at,void *dst,size_t n) {
    (void)ctx;SIZE_T got=0;
    return ReadProcessMemory(GetCurrentProcess(),(void *)(uintptr_t)at,dst,n,&got) && got==n;
}
static uint64_t ticks(void) {LARGE_INTEGER q;QueryPerformanceCounter(&q);return q.QuadPart;}
static uint64_t thread_id(void) {return GetCurrentThreadId();}
uint32_t SnowActionProbe_ABIVersion(void) {return 2;}
size_t SnowActionProbe_RecordSize(void) {return sizeof(SnowActionRecord);}
uint64_t SnowActionProbe_ClockFrequency(void) {LARGE_INTEGER q;return QueryPerformanceFrequency(&q)?(uint64_t)q.QuadPart:0;}
int SnowActionProbe_Configure(uint64_t address,SnowActionOriginal original) {
    return SnowActionProbe_ConfigureObserved(address,original,NULL,NULL);
}
int SnowActionProbe_ConfigureObserved(uint64_t address,SnowActionOriginal original,SnowActionRead reader,void *context) {
    HMODULE pinned;
    if(!address || (address&7) || !original)return 0;
    if(InterlockedCompareExchange(&ready,1,0)!=0)return 0;
    slot_address=address;observe=reader;observe_context=context;
    if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
       (LPCSTR)(uintptr_t)&SnowActionProbe_Configure,&pinned) ||
       !snow_action_trace_init(&trace,records,CAPACITY,original,ticks,thread_id)) {
        InterlockedExchange(&ready,-1);return 0;
    }
    InterlockedExchange(&ready,2);return 1;
}
void SnowActionProbe_Dispatch(void *action) {
    /* Must never be published before successful configuration. */
    if(InterlockedCompareExchange(&ready,2,2)==2)snow_action_trace_call_observed(&trace,action,observe,observe_context);
}
int SnowActionProbe_Close(size_t *used,size_t *dropped) {
    if(InterlockedCompareExchange(&ready,2,2)!=2)return 0;
    snow_action_trace_close(&trace);
    if(!snow_action_trace_drained(&trace))return 0;
    if(used)*used=atomic_load(&trace.used);
    if(dropped)*dropped=atomic_load(&trace.dropped);
    return 1;
}
int SnowActionProbe_ReadRecordSized(size_t i,void *out,size_t n) {
    return InterlockedCompareExchange(&ready,2,2)==2 && snow_action_trace_read(&trace,i,out,n);
}
/* Installer control calls are serialized; actor dispatch never takes this lock. */
static SRWLOCK slot_lock=SRWLOCK_INIT;
static void *volatile *slot;
static DWORD slot_protection;
static int install_attempted, protection_known;
static int restore_slot_locked(void) {
    if(!slot || !protection_known) return 1;
    void *seen=NULL; DWORD previous,ignored;
    if(!read_memory(NULL,(uintptr_t)slot,&seen,sizeof seen)) return 0;
    if(!VirtualProtect((void *)slot,sizeof(void *),PAGE_READWRITE,&previous)) return -1;
    void *mine=(void *)(uintptr_t)&SnowActionProbe_Dispatch;
    seen=InterlockedCompareExchangePointer(slot,(void *)(uintptr_t)trace.original,mine);
    int owned=seen==mine || seen==(void *)(uintptr_t)trace.original;
    /* Restore the recorded original protection even if pointer ownership was lost. */
    if(!VirtualProtect((void *)slot,sizeof(void *),slot_protection,&ignored)) return -1;
    return owned;
}
int SnowActionProbe_InstallSlot(void) {
    int result=0; MEMORY_BASIC_INFORMATION region; HMODULE table_module,target_module,pinned;
    void *seen; DWORD ignored;
    AcquireSRWLockExclusive(&slot_lock);
    if(install_attempted || InterlockedCompareExchange(&ready,2,2)!=2 || (atomic_load(&trace.gate)&(UINT64_C(1)<<63))) goto done;
    install_attempted=1;
    uint64_t address=slot_address;
    if((address&7) ||
       !VirtualQuery((void *)(uintptr_t)address,&region,sizeof region) || region.Type!=MEM_IMAGE ||
       region.State!=MEM_COMMIT || (region.Protect!=PAGE_READONLY && region.Protect!=PAGE_READWRITE &&
                                  region.Protect!=PAGE_WRITECOPY) ||
       address+8>(uint64_t)(uintptr_t)region.BaseAddress+region.RegionSize) goto done;
    DWORD flags=GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT;
    if(!GetModuleHandleExA(flags,(LPCSTR)(uintptr_t)address,&table_module) ||
       !GetModuleHandleExA(flags,(LPCSTR)(uintptr_t)trace.original,&target_module) || table_module!=target_module ||
       !read_memory(NULL,address,&seen,sizeof seen) || seen!=(void *)(uintptr_t)trace.original) goto done;
    if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
                          (LPCSTR)(uintptr_t)address,&pinned)) goto done;
    slot=(void *volatile *)(uintptr_t)address;
    if(!VirtualProtect((void *)slot,8,PAGE_READWRITE,&slot_protection)) { result=-1; goto done; }
    protection_known=1;
    seen=InterlockedCompareExchangePointer(slot,(void *)(uintptr_t)&SnowActionProbe_Dispatch,(void *)(uintptr_t)trace.original);
    result=seen==(void *)(uintptr_t)trace.original;
    if(!VirtualProtect((void *)slot,8,slot_protection,&ignored)) {
        /* Best-effort rollback; RestoreSlot remains available if this fails. */
        restore_slot_locked(); result=-1;
    }
done:
    ReleaseSRWLockExclusive(&slot_lock); return result;
}
int SnowActionProbe_RestoreSlot(void) {
    AcquireSRWLockExclusive(&slot_lock);
    int result=restore_slot_locked();
    ReleaseSRWLockExclusive(&slot_lock); return result;
}
