#define WIN32_LEAN_AND_MEAN
#include "snow_first_write.h"
#include <string.h>
/* 0 unused, 1 armed, 2 restoring, 3 captured, 4 cancelled, 5 failed. */
static volatile LONG state;
static uintptr_t page;
static SIZE_T page_size;
static SnowFirstWriteRecord record;
static int writable(void){
    MEMORY_BASIC_INFORMATION info;
    return VirtualQuery((void *)page,&info,sizeof info) && info.State==MEM_COMMIT && info.Protect==PAGE_READWRITE;
}
static LONG CALLBACK fault(EXCEPTION_POINTERS *e){
    if(!e || !e->ExceptionRecord || !e->ContextRecord)return EXCEPTION_CONTINUE_SEARCH;
    EXCEPTION_RECORD *r=e->ExceptionRecord;
    if(r->ExceptionCode!=EXCEPTION_ACCESS_VIOLATION || r->NumberParameters<2 || (r->ExceptionFlags&EXCEPTION_NONCONTINUABLE) ||
       r->ExceptionInformation[0]!=1 || r->ExceptionInformation[1]<page ||
       r->ExceptionInformation[1]-page>=page_size)return EXCEPTION_CONTINUE_SEARCH;
    LONG seen=InterlockedCompareExchange(&state,2,1);
    if(seen==2)return EXCEPTION_CONTINUE_EXECUTION; /* Another thread restores; retry faulting instruction. */
    if(seen==3 || seen==4)return writable()?EXCEPTION_CONTINUE_EXECUTION:EXCEPTION_CONTINUE_SEARCH;
    if(seen!=1)return EXCEPTION_CONTINUE_SEARCH;
    record.fault_address=r->ExceptionInformation[1];record.instruction=(uintptr_t)r->ExceptionAddress;
    record.context=*e->ContextRecord;record.thread=GetCurrentThreadId();
    LARGE_INTEGER tick;QueryPerformanceCounter(&tick);record.tick=(uint64_t)tick.QuadPart;
    DWORD old;
    if(!VirtualProtect((void *)page,page_size,PAGE_READWRITE,&old)){
        InterlockedExchange(&state,5);return EXCEPTION_CONTINUE_SEARCH;
    }
    InterlockedExchange(&state,3);
    return EXCEPTION_CONTINUE_EXECUTION;
}
int snow_first_write_arm(void *address){
    if(InterlockedCompareExchange(&state,5,0)!=0)return 0;
    SYSTEM_INFO system;GetSystemInfo(&system);page_size=system.dwPageSize;
    page=(uintptr_t)address-((uintptr_t)address%page_size);
    MEMORY_BASIC_INFORMATION info;
    if(!address || !VirtualQuery((void *)page,&info,sizeof info) || info.State!=MEM_COMMIT ||
       info.Protect!=PAGE_READWRITE || (info.Type!=MEM_PRIVATE && info.Type!=MEM_IMAGE) ||
       ((uintptr_t)&state>=page && (uintptr_t)&state-page<page_size) ||
       ((uintptr_t)&record<page+page_size && (uintptr_t)&record+sizeof record>page) ||
       ((uintptr_t)&page>=page && (uintptr_t)&page-page<page_size) ||
       ((uintptr_t)&page_size>=page && (uintptr_t)&page_size-page<page_size))return 0;
    HMODULE pinned;
    if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
                          (LPCSTR)(uintptr_t)&fault,&pinned) || !AddVectoredExceptionHandler(1,fault))return 0;
    InterlockedExchange(&state,1);
    DWORD old;
    if(!VirtualProtect((void *)page,page_size,PAGE_READONLY,&old)){
        InterlockedExchange(&state,5);return 0;
    }
    return 1;
}
int snow_first_write_cancel(void){
    LONG seen=InterlockedCompareExchange(&state,2,1);
    if(seen==3 || seen==4)return 1;
    if(seen!=1)return 0;
    DWORD old;
    if(!VirtualProtect((void *)page,page_size,PAGE_READWRITE,&old)){
        InterlockedExchange(&state,5);return 0;
    }
    InterlockedExchange(&state,4);return 1;
}
int snow_first_write_read(SnowFirstWriteRecord *out){
    if(!out || InterlockedCompareExchange(&state,0,0)!=3)return 0;
    *out=record;return 1;
}
