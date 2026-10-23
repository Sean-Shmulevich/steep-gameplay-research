/* Build-specific continuation identity + optional authored-page control.
 * Never changes game-page permissions or installs/removes a hook. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "snow_plugin.h"
#include "snow_continuation_identity.h"
#include "snow_first_execute.h"
typedef LONG (WINAPI *NativeProtect)(HANDLE,PVOID *,SIZE_T *,ULONG,PULONG);
typedef ULONG (WINAPI *StatusError)(LONG);
static struct { NativeProtect call;StatusError error;volatile LONG calls,last_status; } provider;
static BOOL protect_backend(void *ctx,void *address,SIZE_T size,DWORD protection,DWORD *old){
    if(ctx!=&provider || !provider.call){SetLastError(ERROR_INVALID_PARAMETER);return FALSE;}
    PVOID p=address;SIZE_T n=size;
    LONG status=provider.call(GetCurrentProcess(),&p,&n,protection,old);
    InterlockedIncrement(&provider.calls);InterlockedExchange(&provider.last_status,status);
    if(status<0){SetLastError(provider.error?provider.error(status):ERROR_GEN_FAILURE);return FALSE;}
    return TRUE;
}
static int read_at(uintptr_t address,void *out,SIZE_T size){
    MEMORY_BASIC_INFORMATION info;SIZE_T got=0;
    if(address<0x10000 || address>UINT64_C(0x7fffffffffff)-size ||
       !VirtualQuery((void *)address,&info,sizeof info) || info.State!=MEM_COMMIT ||
       (info.Protect&(PAGE_GUARD|PAGE_NOACCESS)) ||
       size>info.RegionSize-(address-(uintptr_t)info.BaseAddress))return 0;
    return ReadProcessMemory(GetCurrentProcess(),(void *)address,out,size,&got)&&got==size;
}
static int fingerprint(uintptr_t address){
    unsigned char code[32];if(!read_at(address,code,sizeof code))return 0;
    uint64_t h=UINT64_C(14695981039346656037);
    for(unsigned i=0;i<sizeof code;i++)h=(h^code[i])*UINT64_C(1099511628211);
    return h==UINT64_C(0x1456172a4e7c2ca7);
}
__declspec(dllexport) int SnowMod_Initialize(const SnowHostApiV1 *api,SnowPluginV1 *plugin){
    if(!api || !plugin || api->api_version!=SNOW_PLUGIN_API_VERSION || api->struct_size<sizeof *api ||
       !api->config_path || strlen(api->config_path)+13>=MAX_PATH ||
       GetPrivateProfileIntA("continuation","enabled",0,api->config_path)!=1)return 1;
    uintptr_t base=(uintptr_t)GetModuleHandleW(NULL),context=0,again=0,candidate_again=0;
    int compatible=fingerprint(base+0x4122688),sampled=0,joined=0,rechecked=0,pinned=0;
    SnowContinuationSample sample={0},second={0};MEMORY_BASIC_INFORMATION ci={0},ei={0};
    HMODULE ntdll=GetModuleHandleA("ntdll.dll"),pin=NULL;
    sample.entry=ntdll?(uintptr_t)GetProcAddress(ntdll,"NtProtectVirtualMemory"):0;
    sample.expected_handler=base+0x3565850;
    if(compatible && read_at(base+0x3595838,&context,8) && context>=0x10000 &&
       context<=UINT64_C(0x7fffffffffff)-0x80 && read_at(context+0x78,&sample.candidate,8)){
        sampled=read_at(sample.entry,sample.entry_bytes,sizeof sample.entry_bytes) &&
            read_at(sample.candidate,sample.candidate_bytes,sizeof sample.candidate_bytes);
        if(sampled && VirtualQuery((void *)sample.entry,&ei,sizeof ei) && ei.Type==MEM_IMAGE && ei.AllocationBase==ntdll &&
           VirtualQuery((void *)sample.candidate,&ci,sizeof ci) && ci.Type==MEM_PRIVATE && ci.Protect==PAGE_EXECUTE_READ)
            joined=snow_continuation_matches(&sample,UINT64_C(0x505379c67bb2335a),UINT64_C(0x549a5fa99d8767b3));
    }
    if(joined){
        second=sample;
        pinned=GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)sample.entry,&pin);
        rechecked=read_at(base+0x3595838,&again,8) && again==context && read_at(context+0x78,&candidate_again,8) &&
            candidate_again==sample.candidate && read_at(sample.entry,second.entry_bytes,sizeof second.entry_bytes) &&
            read_at(sample.candidate,second.candidate_bytes,sizeof second.candidate_bytes) && !memcmp(&sample,&second,sizeof sample);
    }
    int exercise=GetPrivateProfileIntA("continuation","exercise",0,api->config_path)==1;
    int observer=GetPrivateProfileIntA("continuation","observer",0,api->config_path)==1;
    int configured=0,armed=0,captured=0,exact=0,cancelled=0,retained=0;uint64_t function_result=0;
    unsigned arm_stage=0;DWORD arm_error=0;
    int allocated=0,initial_rx=0,called=0,rounded=0,restored_call=0,fallback=0,released=0,bytes_equal=0;
    LONG status=(LONG)0xc0000001,restore_status=(LONG)0xc0000001;ULONG old_protection=0,restore_old=0;
    DWORD observed=0,final_protection=0;SYSTEM_INFO system;GetSystemInfo(&system);
    if(exercise && joined && rechecked && pinned){
        unsigned char *page=VirtualAlloc(NULL,system.dwPageSize,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
        allocated=page!=NULL;
        if(page){
            unsigned char payload[32];memset(payload,0xa5,sizeof payload);
            if(observer){const unsigned char function[]={0xb8,42,0,0,0,0xc3};memcpy(payload,function,sizeof function);}
            memcpy(page,payload,sizeof payload);DWORD old;
            initial_rx=VirtualProtect(page,system.dwPageSize,PAGE_EXECUTE_READ,&old);
            if(initial_rx && observer){
                provider.call=(NativeProtect)sample.candidate;
                provider.error=(StatusError)(uintptr_t)GetProcAddress(ntdll,"RtlNtStatusToDosError");
                if(FlushInstructionCache(GetCurrentProcess(),page,sizeof payload)){
                    configured=snow_first_execute_backend(protect_backend,&provider);
                    if(configured)armed=snow_first_execute_arm(page);
                }
                snow_first_execute_arm_diagnostic(&arm_stage,&arm_error);
                if(armed){
                    typedef uint64_t (*Function)(void);function_result=((Function)(uintptr_t)page)();
                    SnowFirstExecuteRecord record;captured=snow_first_execute_read(&record);
                    exact=captured && record.instruction==(uintptr_t)page;
                    cancelled=snow_first_execute_cancel();
                }
                MEMORY_BASIC_INFORMATION info={0};VirtualQuery(page,&info,sizeof info);
                if(info.Protect!=PAGE_EXECUTE_READ)fallback=VirtualProtect(page,system.dwPageSize,PAGE_EXECUTE_READ,&old);
                VirtualQuery(page,&info,sizeof info);final_protection=info.Protect;
                unsigned char bytes[32];bytes_equal=read_at((uintptr_t)page,bytes,sizeof bytes) && !memcmp(bytes,payload,sizeof bytes);
            }else if(initial_rx){
                typedef LONG (WINAPI *Protect)(HANDLE,PVOID *,SIZE_T *,ULONG,PULONG);
                Protect protect=(Protect)sample.candidate;PVOID address=page+13;SIZE_T length=7;
                status=protect(GetCurrentProcess(),&address,&length,PAGE_READONLY,&old_protection);called=1;
                rounded=address==page && length==system.dwPageSize;
                MEMORY_BASIC_INFORMATION info={0};VirtualQuery(page,&info,sizeof info);observed=info.Protect;
                address=page;length=system.dwPageSize;
                restore_status=protect(GetCurrentProcess(),&address,&length,PAGE_EXECUTE_READ,&restore_old);restored_call=1;
                VirtualQuery(page,&info,sizeof info);
                if(info.Protect!=PAGE_EXECUTE_READ)fallback=VirtualProtect(page,system.dwPageSize,PAGE_EXECUTE_READ,&old);
                VirtualQuery(page,&info,sizeof info);final_protection=info.Protect;
                unsigned char bytes[32];bytes_equal=read_at((uintptr_t)page,bytes,sizeof bytes);
                if(bytes_equal)for(unsigned i=0;i<sizeof bytes;i++)if(bytes[i]!=0xa5)bytes_equal=0;
            }
            if(observer)retained=1;else released=VirtualFree(page,0,MEM_RELEASE);
        }
    }
    char output[MAX_PATH];snprintf(output,sizeof output,"%s.join.json",api->config_path);FILE *f=fopen(output,"w");if(!f)return 1;
    fprintf(f,"{\"compatible\":%d,\"sampled\":%d,\"joined\":%d,\"rechecked\":%d,\"ntdll_pinned\":%d,"
        "\"entry\":\"%llx\",\"candidate\":\"%llx\",\"context\":\"%llx\",\"exercise\":%d,"
        "\"allocated\":%d,\"initial_rx\":%d,\"called\":%d,\"status\":\"%08lx\",\"rounded\":%d,"
        "\"old_protection\":%lu,\"observed_protection\":%lu,\"restore_called\":%d,\"restore_status\":\"%08lx\","
        "\"restore_old\":%lu,\"fallback\":%d,\"final_protection\":%lu,\"bytes_equal\":%d,\"released\":%d,",
        compatible,sampled,joined,rechecked,pinned,(unsigned long long)sample.entry,(unsigned long long)sample.candidate,
        (unsigned long long)context,exercise,allocated,initial_rx,called,(unsigned long)status,rounded,
        (unsigned long)old_protection,(unsigned long)observed,restored_call,(unsigned long)restore_status,
        (unsigned long)restore_old,fallback,(unsigned long)final_protection,bytes_equal,released);
    fprintf(f,"\"observer\":%d,\"backend_configured\":%d,\"armed\":%d,\"arm_stage\":%u,\"arm_error\":%lu,"
        "\"captured\":%d,\"exact_entry\":%d,\"cancel_returned\":%d,\"function_result\":%llu,"
        "\"backend_calls\":%ld,\"backend_last_status\":\"%08lx\",\"retained_until_exit\":%d}\n",
        observer,configured,armed,arm_stage,(unsigned long)arm_error,captured,exact,cancelled,
        (unsigned long long)function_result,provider.calls,(unsigned long)provider.last_status,retained);fclose(f);
    plugin->struct_size=sizeof *plugin;plugin->api_version=SNOW_PLUGIN_API_VERSION;
    plugin->name="protection_continuation_control";plugin->version="experimental-1";return 0;
}
