#define WIN32_LEAN_AND_MEAN
#include "snow_first_execute.h"
#include <string.h>
/* 0 unused, 1 armed, 2 restoring, 3 captured, 4 cancelled, 5 failed. */
static volatile LONG state;
static uintptr_t page;
static SIZE_T page_size;
static SnowFirstExecuteRecord record;
static unsigned arm_stage;
static DWORD arm_error;
static SnowExecuteProtect backend;
static void *backend_context;
int snow_first_execute_backend(SnowExecuteProtect protect,void *context){
    if(!protect || InterlockedCompareExchange(&state,0,0)!=0)return 0;
    backend=protect;backend_context=context;return 1;
}
static int change_protection(DWORD protection){
    DWORD old;BOOL ok=backend?backend(backend_context,(void *)page,page_size,protection,&old):
        VirtualProtect((void *)page,page_size,protection,&old);
    if(!ok)return 0;
    MEMORY_BASIC_INFORMATION info;
    if(!VirtualQuery((void *)page,&info,sizeof info) || info.State!=MEM_COMMIT){
        SetLastError(ERROR_INVALID_DATA);return 0;
    }
    if(info.Protect!=protection){
        /* Execution can fault and restore RX before Arm's backend returns. */
        LONG seen=InterlockedCompareExchange(&state,0,0);
        if(protection==PAGE_READONLY && info.Protect==PAGE_EXECUTE_READ && (seen==2 || seen==3))return 1;
        SetLastError(ERROR_INVALID_DATA);return 0;
    }
    return 1;
}
void snow_first_execute_arm_diagnostic(unsigned *stage,DWORD *error){
    if(stage)*stage=arm_stage;
    if(error)*error=arm_error;
}
static int executable(void){
    MEMORY_BASIC_INFORMATION info;
    return VirtualQuery((void *)page,&info,sizeof info) &&
        info.State==MEM_COMMIT && info.Protect==PAGE_EXECUTE_READ;
}
static void snapshot_stack(void){
    uintptr_t address=(uintptr_t)record.context.Rsp;
    MEMORY_BASIC_INFORMATION info;
    if(address<0x10000 || address>UINT64_C(0x7fffffffffff)-sizeof record.stack ||
       !VirtualQuery((void *)address,&info,sizeof info) || info.State!=MEM_COMMIT ||
       (info.Protect&(PAGE_GUARD|PAGE_NOACCESS)) ||
       address-(uintptr_t)info.BaseAddress>info.RegionSize ||
       sizeof record.stack>info.RegionSize-(address-(uintptr_t)info.BaseAddress))return;
    SIZE_T got=0;
    record.stack_valid=ReadProcessMemory(GetCurrentProcess(),(void *)address,
        record.stack,sizeof record.stack,&got) && got==sizeof record.stack;
    if(!record.stack_valid)memset(record.stack,0,sizeof record.stack);
}
static LONG CALLBACK fault(EXCEPTION_POINTERS *e){
    if(!e || !e->ExceptionRecord || !e->ContextRecord)return EXCEPTION_CONTINUE_SEARCH;
    EXCEPTION_RECORD *r=e->ExceptionRecord;
    if(r->ExceptionCode!=EXCEPTION_ACCESS_VIOLATION || r->NumberParameters<2 ||
       (r->ExceptionFlags&EXCEPTION_NONCONTINUABLE) || r->ExceptionInformation[0]!=8 ||
       r->ExceptionInformation[1]<page || r->ExceptionInformation[1]-page>=page_size ||
       e->ContextRecord->Rip<page || e->ContextRecord->Rip-page>=page_size)
        return EXCEPTION_CONTINUE_SEARCH;
    LONG seen=InterlockedCompareExchange(&state,2,1);
    if(seen==2)return EXCEPTION_CONTINUE_EXECUTION;
    if(seen==3 || seen==4)return executable()?EXCEPTION_CONTINUE_EXECUTION:EXCEPTION_CONTINUE_SEARCH;
    if(seen!=1)return EXCEPTION_CONTINUE_SEARCH;
    record.fault_address=r->ExceptionInformation[1];record.instruction=e->ContextRecord->Rip;
    record.context=*e->ContextRecord;record.thread=GetCurrentThreadId();
    LARGE_INTEGER tick;QueryPerformanceCounter(&tick);record.tick=(uint64_t)tick.QuadPart;
    snapshot_stack();
    if(!change_protection(PAGE_EXECUTE_READ)){
        InterlockedExchange(&state,5);return EXCEPTION_CONTINUE_SEARCH;
    }
    InterlockedExchange(&state,3);return EXCEPTION_CONTINUE_EXECUTION;
}
int snow_first_execute_arm(void *address){
    if(InterlockedCompareExchange(&state,5,0)!=0)return 0;
    arm_stage=1;
    SYSTEM_INFO system;GetSystemInfo(&system);page_size=system.dwPageSize;
    page=(uintptr_t)address-((uintptr_t)address%page_size);
    MEMORY_BASIC_INFORMATION info, own;
    if(!address || !VirtualQuery((void *)page,&info,sizeof info) || info.State!=MEM_COMMIT ||
       info.Protect!=PAGE_EXECUTE_READ || (info.Type!=MEM_PRIVATE && info.Type!=MEM_IMAGE) ||
       !VirtualQuery((void *)(uintptr_t)&fault,&own,sizeof own))return 0;
    arm_stage=2;if(info.AllocationBase==own.AllocationBase)return 0;
    if(backend){
        MEMORY_BASIC_INFORMATION provider;
        if(!VirtualQuery((void *)(uintptr_t)backend,&provider,sizeof provider) ||
           provider.AllocationBase==info.AllocationBase ||
           ((uintptr_t)backend_context>=page && (uintptr_t)backend_context-page<page_size))return 0;
    }
    /* Reject the entire observer module, including its data and helper code. */
    HMODULE pinned;
    arm_stage=3;
    if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
       (LPCSTR)(uintptr_t)&fault,&pinned)){arm_error=GetLastError();return 0;}
    if(backend && !GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
       (LPCSTR)(uintptr_t)backend,&pinned)){arm_error=GetLastError();return 0;}
    arm_stage=4;
    if(!AddVectoredExceptionHandler(1,fault)){arm_error=GetLastError();return 0;}
    InterlockedExchange(&state,1);
    arm_stage=5;
    if(!change_protection(PAGE_READONLY)){
        arm_error=GetLastError();
        InterlockedExchange(&state,5);return 0;
    }
    arm_stage=6;
    return 1;
}
int snow_first_execute_cancel(void){
    LONG seen=InterlockedCompareExchange(&state,2,1);
    if(seen==3 || seen==4)return 1;
    if(seen!=1)return 0;
    if(!change_protection(PAGE_EXECUTE_READ)){
        InterlockedExchange(&state,5);return 0;
    }
    InterlockedExchange(&state,4);return 1;
}
int snow_first_execute_read(SnowFirstExecuteRecord *out){
    if(!out || InterlockedCompareExchange(&state,0,0)!=3)return 0;
    *out=record;return 1;
}
