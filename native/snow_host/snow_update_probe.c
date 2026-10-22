#define WIN32_LEAN_AND_MEAN
#define SNOW_UPDATE_PROBE_BUILD
#include <windows.h>
#include <string.h>
#include "snow_update_probe.h"
#define CAPACITY 4096
static SnowUpdateTrace trace;
static SnowUpdateRecord records[CAPACITY];
static SnowUpdateBinding binding;
static LONG ready;
static SnowEntryProfile entry_profile;
static int attributed;
static volatile LONG64 selected_calls,other_calls;
static int read_memory(void *ctx,uint64_t at,void *dst,size_t n) {
    (void)ctx; SIZE_T got=0;
    return ReadProcessMemory(GetCurrentProcess(),(const void *)(uintptr_t)at,dst,n,&got) && got==n;
}
static void snapshot(void *actor,SnowUpdateSnapshot *out) {
    (void)actor; snow_update_snapshot(read_memory,NULL,&binding,out);
}
static uint64_t ticks(void) { LARGE_INTEGER q; QueryPerformanceCounter(&q); return (uint64_t)q.QuadPart; }
static uint64_t thread_id(void) { return GetCurrentThreadId(); }
static int configure(const SnowUpdateBinding *b,SnowUpdateOriginal original,const SnowEntryProfile *profile) {
    HMODULE module; SnowUpdateSnapshot check;
    if(!b || !original) return 0;
    if(InterlockedCompareExchange(&ready,1,0)!=0) return 0;
    binding=*b;
    attributed=profile!=NULL;
    if(profile) entry_profile=*profile;
    if(!snow_update_snapshot(read_memory,NULL,&binding,&check) ||
       !GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
                          (LPCSTR)(uintptr_t)&SnowProbe_Configure,&module) ||
       !snow_trace_init(&trace,records,CAPACITY,original,snapshot,ticks,thread_id)) {
        InterlockedExchange(&ready,-1); return 0;
    }
    InterlockedExchange(&ready,2); return 1;
}
int SnowProbe_Configure(const SnowUpdateBinding *b,SnowUpdateOriginal original) {
    return configure(b,original,NULL);
}
int SnowProbe_ConfigureAttributed(const SnowUpdateBinding *b,SnowUpdateOriginal original,
                                  const SnowEntryProfile *profile) {
    if(!profile || !b || profile->actor_table!=b->actor_table || !profile->job_table ||
       !profile->callable_table || !profile->return_address) return 0;
    return configure(b,original,profile);
}
typedef struct { const SnowEntryRegisters *entry; uint64_t actor; uint32_t elapsed,consumed; } EntryContext;
static int attribute_entry(void *context,SnowEntryAttribution *out,SnowBatchFrame *frame) {
    EntryContext *c=context;
    if(!snow_entry_attribute(read_memory,NULL,&entry_profile,c->entry,c->actor,out)) return 0;
    if(entry_profile.batch_return && snow_batch_frame(read_memory,NULL,out->job,
           entry_profile.batch_return,binding.world,c->elapsed,c->consumed,frame)) return 3;
    return 1;
}
void SnowProbe_EntryDispatch(void *actor,float elapsed,float derivative,const SnowEntryRegisters *entry) {
    if(InterlockedCompareExchange(&ready,2,2)!=2) return;
    if((uint64_t)(uintptr_t)actor!=binding.actor) {
        InterlockedIncrement64(&other_calls);
        trace.original(actor,elapsed,derivative); return;
    }
    InterlockedIncrement64(&selected_calls);
    EntryContext context={entry,(uint64_t)(uintptr_t)actor,0,0};
    memcpy(&context.elapsed,&elapsed,4);memcpy(&context.consumed,&derivative,4);
    snow_trace_call_attributed(&trace,actor,elapsed,derivative,attribute_entry,&context);
}
static void *dispatch_target(void) {
    return attributed ? (void *)(uintptr_t)&SnowProbe_EntryThunk : (void *)(uintptr_t)&SnowProbe_Dispatch;
}
void SnowProbe_Dispatch(void *actor,float elapsed,float derivative) {
    /* Publishing before Configure succeeds violates the ABI. Never install until ready. */
    if(InterlockedCompareExchange(&ready,2,2)!=2) return;
    if((uint64_t)(uintptr_t)actor!=binding.actor) {
        InterlockedIncrement64(&other_calls);
        trace.original(actor,elapsed,derivative); return;
    }
    InterlockedIncrement64(&selected_calls);
    snow_trace_call(&trace,actor,elapsed,derivative);
}
int SnowProbe_ReadDispatchCounts(SnowProbeDispatchCounts *out) {
    if(!out) return 0;
    out->selected_calls=out->other_calls=0;
    if(InterlockedCompareExchange(&ready,2,2)!=2) return 0;
    out->selected_calls=(uint64_t)InterlockedCompareExchange64(&selected_calls,0,0);
    out->other_calls=(uint64_t)InterlockedCompareExchange64(&other_calls,0,0);
    return 1;
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
    void *mine=dispatch_target();
    seen=InterlockedCompareExchangePointer(slot,(void *)(uintptr_t)trace.original,mine);
    int owned=seen==mine || seen==(void *)(uintptr_t)trace.original;
    /* Restore the recorded original protection even if pointer ownership was lost. */
    if(!VirtualProtect((void *)slot,sizeof(void *),slot_protection,&ignored)) return -1;
    return owned;
}
int SnowProbe_InstallSlot(void) {
    int result=0; MEMORY_BASIC_INFORMATION region; HMODULE table_module,target_module,pinned;
    SnowUpdateSnapshot check; void *seen; DWORD ignored;
    AcquireSRWLockExclusive(&slot_lock);
    if(install_attempted || InterlockedCompareExchange(&ready,2,2)!=2 || (atomic_load(&trace.gate)&(UINT64_C(1)<<63))) goto done;
    install_attempted=1;
    if(!snow_update_snapshot(read_memory,NULL,&binding,&check)) goto done;
    uint64_t address=binding.actor_table+0x2c0;
    if(address<binding.actor_table || (address&7) ||
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
    seen=InterlockedCompareExchangePointer(slot,dispatch_target(),(void *)(uintptr_t)trace.original);
    result=seen==(void *)(uintptr_t)trace.original;
    if(!VirtualProtect((void *)slot,8,slot_protection,&ignored)) {
        /* Best-effort rollback; RestoreSlot remains available if this fails. */
        restore_slot_locked(); result=-1;
    }
done:
    ReleaseSRWLockExclusive(&slot_lock); return result;
}
int SnowProbe_RestoreSlot(void) {
    AcquireSRWLockExclusive(&slot_lock);
    int result=restore_slot_locked();
    ReleaseSRWLockExclusive(&slot_lock); return result;
}
