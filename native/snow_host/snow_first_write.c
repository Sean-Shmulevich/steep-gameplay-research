#define WIN32_LEAN_AND_MEAN
#include "snow_first_write.h"
#include <string.h>
/* 0 unused, 1 armed, 2 restoring, 3 captured, 4 cancelled, 5 failed. */
static volatile LONG state;
static uintptr_t page;
static SIZE_T page_size;
static DWORD original_protection;
static SnowFirstWriteRecord record;
static SnowWriteWindowSpec specs[SNOW_FIRST_WRITE_WINDOWS];
static uint32_t window_count;
int snow_first_write_windows(const SnowWriteWindowSpec *input,uint32_t count){
    if(InterlockedCompareExchange(&state,0,0)!=0 || count>SNOW_FIRST_WRITE_WINDOWS || (count && !input))return 0;
    for(uint32_t i=0;i<count;i++)
        if(input[i].source<SNOW_WRITE_RSP || input[i].source>SNOW_WRITE_FAULT ||
           input[i].offset < -4096 || input[i].offset>4096 || !input[i].size || input[i].size>SNOW_FIRST_WRITE_WINDOW_BYTES)return 0;
    if(count)memcpy(specs,input,count*sizeof *input);
    window_count=count;return 1;
}
static void snapshot_windows(void){
    record.window_count=window_count;
    for(uint32_t i=0;i<window_count;i++){
        SnowWriteWindow *out=&record.windows[i];SnowWriteWindowSpec *s=&specs[i];
        uint64_t address=s->source==SNOW_WRITE_RSP?record.context.Rsp:
            s->source==SNOW_WRITE_RBP?record.context.Rbp:s->source==SNOW_WRITE_RBX?record.context.Rbx:record.fault_address;
        out->size=s->size;
        if(s->offset<0){if(address<(uint64_t)(-(int64_t)s->offset))continue;address-=(uint64_t)(-(int64_t)s->offset);}
        else{if(address>UINT64_MAX-(uint32_t)s->offset)continue;address+=(uint32_t)s->offset;}
        out->address=(uintptr_t)address;
        if(address<0x10000 || address>UINT64_C(0x7fffffffffff)-s->size)continue;
        MEMORY_BASIC_INFORMATION info;
        if(!VirtualQuery((void *)(uintptr_t)address,&info,sizeof info) || info.State!=MEM_COMMIT ||
           (info.Protect&(PAGE_GUARD|PAGE_NOACCESS)) || address-(uintptr_t)info.BaseAddress>info.RegionSize ||
           s->size>info.RegionSize-(address-(uintptr_t)info.BaseAddress))continue;
        SIZE_T got=0;
        out->valid=ReadProcessMemory(GetCurrentProcess(),(void *)(uintptr_t)address,out->bytes,s->size,&got)&&got==s->size;
        if(!out->valid)memset(out->bytes,0,sizeof out->bytes);
    }
}
static int writable(void){
    MEMORY_BASIC_INFORMATION info;
    return VirtualQuery((void *)page,&info,sizeof info) && info.State==MEM_COMMIT && (info.Protect==original_protection ||
        (original_protection==PAGE_WRITECOPY && info.Protect==PAGE_READWRITE));
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
    snapshot_windows();
    DWORD old;
    if(!VirtualProtect((void *)page,page_size,original_protection,&old)){
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
       (info.Protect!=PAGE_READWRITE && !(info.Type==MEM_IMAGE && info.Protect==PAGE_WRITECOPY)) ||
       (info.Type!=MEM_PRIVATE && info.Type!=MEM_IMAGE) ||
       ((uintptr_t)&state>=page && (uintptr_t)&state-page<page_size) ||
       ((uintptr_t)&record<page+page_size && (uintptr_t)&record+sizeof record>page) ||
       ((uintptr_t)&page>=page && (uintptr_t)&page-page<page_size) ||
       ((uintptr_t)&page_size>=page && (uintptr_t)&page_size-page<page_size) ||
       ((uintptr_t)&original_protection>=page && (uintptr_t)&original_protection-page<page_size) ||
       ((uintptr_t)&specs<page+page_size && (uintptr_t)&specs+sizeof specs>page) ||
       ((uintptr_t)&window_count>=page && (uintptr_t)&window_count-page<page_size))return 0;
    original_protection=info.Protect;
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
    if(!VirtualProtect((void *)page,page_size,original_protection,&old)){
        InterlockedExchange(&state,5);return 0;
    }
    InterlockedExchange(&state,4);return 1;
}
int snow_first_write_read(SnowFirstWriteRecord *out){
    if(!out || InterlockedCompareExchange(&state,0,0)!=3)return 0;
    *out=record;return 1;
}
