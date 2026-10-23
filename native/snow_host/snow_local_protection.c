#define WIN32_LEAN_AND_MEAN
#include "snow_local_protection.h"
#include "snow_continuation_identity.h"
#include <string.h>
static int read_at(uintptr_t address,void *out,SIZE_T size){
    MEMORY_BASIC_INFORMATION info;SIZE_T got=0;
    if(address<0x10000 || address>UINT64_C(0x7fffffffffff)-size ||
       !VirtualQuery((void *)address,&info,sizeof info) || info.State!=MEM_COMMIT ||
       (info.Protect&(PAGE_GUARD|PAGE_NOACCESS)) || size>info.RegionSize-(address-(uintptr_t)info.BaseAddress))return 0;
    return ReadProcessMemory(GetCurrentProcess(),(void *)address,out,size,&got)&&got==size;
}
int snow_local_protection_resolve(SnowLocalProtection *out){
    if(!out)return 0;
    memset(out,0,sizeof *out);uintptr_t base=(uintptr_t)GetModuleHandleW(NULL),context=0,again=0,candidate_again=0;
    unsigned char code[32];uint64_t hash=UINT64_C(14695981039346656037);
    if(!read_at(base+0x4122688,code,sizeof code))return 0;
    for(unsigned i=0;i<sizeof code;i++)hash=(hash^code[i])*UINT64_C(1099511628211);
    out->compatible=hash==UINT64_C(0x1456172a4e7c2ca7);if(!out->compatible)return 0;
    SnowContinuationSample sample={0},second={0};MEMORY_BASIC_INFORMATION ci={0},ei={0};
    HMODULE ntdll=GetModuleHandleA("ntdll.dll"),pin=NULL;
    sample.entry=ntdll?(uintptr_t)GetProcAddress(ntdll,"NtProtectVirtualMemory"):0;sample.expected_handler=base+0x3565850;
    if(!read_at(base+0x3595838,&context,8) || context<0x10000 || context>UINT64_C(0x7fffffffffff)-0x80 ||
       !read_at(context+0x78,&sample.candidate,8))return 0;
    out->sampled=read_at(sample.entry,sample.entry_bytes,sizeof sample.entry_bytes) &&
        read_at(sample.candidate,sample.candidate_bytes,sizeof sample.candidate_bytes);
    if(out->sampled && VirtualQuery((void *)sample.entry,&ei,sizeof ei) && ei.Type==MEM_IMAGE && ei.AllocationBase==ntdll &&
       VirtualQuery((void *)sample.candidate,&ci,sizeof ci) && ci.Type==MEM_PRIVATE && ci.Protect==PAGE_EXECUTE_READ)
        out->joined=snow_continuation_matches(&sample,UINT64_C(0x505379c67bb2335a),UINT64_C(0x549a5fa99d8767b3));
    if(!out->joined)return 0;
    second=sample;
    out->pinned=GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)sample.entry,&pin);
    out->rechecked=read_at(base+0x3595838,&again,8) && again==context && read_at(context+0x78,&candidate_again,8) &&
        candidate_again==sample.candidate && read_at(sample.entry,second.entry_bytes,sizeof second.entry_bytes) &&
        read_at(sample.candidate,second.candidate_bytes,sizeof second.candidate_bytes) && !memcmp(&sample,&second,sizeof sample);
    if(!out->pinned || !out->rechecked)return 0;
    out->call=(SnowNativeProtect)sample.candidate;
    out->error=(SnowStatusError)(uintptr_t)GetProcAddress(ntdll,"RtlNtStatusToDosError");return 1;
}
BOOL snow_local_protection_apply(void *context,void *address,SIZE_T size,DWORD protection,DWORD *old){
    SnowLocalProtection *p=context;
    if(!p || !p->call || !p->joined || !p->rechecked || !p->pinned){SetLastError(ERROR_INVALID_PARAMETER);return FALSE;}
    PVOID base=address;SIZE_T length=size;LONG status=p->call(GetCurrentProcess(),&base,&length,protection,old);
    InterlockedIncrement(&p->calls);InterlockedExchange(&p->last_status,status);
    if(status<0){SetLastError(p->error?p->error(status):ERROR_GEN_FAILURE);return FALSE;}
    return TRUE;
}
