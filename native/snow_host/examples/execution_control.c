/* Authored control allocation for the execution observer. No game-page writes,
 * game function calls or game addresses. Allocation stays alive through exit. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "snow_plugin.h"
#include "snow_first_execute.h"
static void api_identity(FILE *f,const char *label,uintptr_t address){
    HMODULE module=NULL;char path[MAX_PATH]={0};MEMORY_BASIC_INFORMATION info={0};
    int module_ok=GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|
        GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCSTR)address,&module);
    if(module_ok)GetModuleFileNameA(module,path,sizeof path);
    const char *name=strrchr(path,'\\');name=name?name+1:path;
    int queried=VirtualQuery((void *)address,&info,sizeof info)!=0;
    fprintf(f,"\"%s\":{\"address\":\"%llx\",\"module_ok\":%d,\"module\":\"",
        label,(unsigned long long)address,module_ok);
    /* Emit only printable basename characters safe in JSON. */
    for(const char *p=name;*p;p++)if(*p>=32 && *p<127 && *p!='"' && *p!='\\')fputc(*p,f);
    fprintf(f,"\",\"module_offset\":\"%llx\",\"query\":%d,\"protection\":%lu,\"type\":%lu}",
        (unsigned long long)(module_ok?address-(uintptr_t)module:0),queried,
        (unsigned long)info.Protect,(unsigned long)info.Type);
}
__declspec(dllexport) int SnowMod_Initialize(const SnowHostApiV1 *api,SnowPluginV1 *plugin){
    if(!api || !plugin || api->api_version!=SNOW_PLUGIN_API_VERSION || api->struct_size<sizeof *api ||
       !api->config_path || strlen(api->config_path)+14>=MAX_PATH ||
       GetPrivateProfileIntA("control","enabled",0,api->config_path)!=1)return 1;
    char output[MAX_PATH];snprintf(output,sizeof output,"%s.control.json",api->config_path);
    FILE *f=fopen(output,"w");if(!f)return 1;
    SYSTEM_INFO system;GetSystemInfo(&system);
    unsigned char *page=VirtualAlloc(NULL,system.dwPageSize,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    DWORD alloc_error=page?0:GetLastError(),rx_error=0,flush_error=0,old=0;
    int rx=0,flushed=0,armed=0,captured=0,restored=0,executed=0,bytes_equal=0;
    uint64_t result=0;SnowFirstExecuteRecord record={0};
    const unsigned char code[]={0xb8,42,0,0,0,0xc3}; /* mov eax,42; ret */
    MEMORY_BASIC_INFORMATION before={0},after_arm={0},after={0};
    if(page){
        memcpy(page,code,sizeof code);
        rx=VirtualProtect(page,system.dwPageSize,PAGE_EXECUTE_READ,&old);if(!rx)rx_error=GetLastError();
        if(rx){flushed=FlushInstructionCache(GetCurrentProcess(),page,sizeof code);if(!flushed)flush_error=GetLastError();}
        VirtualQuery(page,&before,sizeof before);
        if(rx && flushed)armed=snow_first_execute_arm(page);
        VirtualQuery(page,&after_arm,sizeof after_arm);
        if(armed){
            typedef uint64_t (*Function)(void);
            result=((Function)(uintptr_t)page)();executed=1;
            captured=snow_first_execute_read(&record);restored=snow_first_execute_cancel();
        }
        VirtualQuery(page,&after,sizeof after);bytes_equal=!memcmp(page,code,sizeof code);
    }
    unsigned stage=0;DWORD error=0;snow_first_execute_arm_diagnostic(&stage,&error);
    fprintf(f,"{\"allocated\":%d,\"allocation_error\":%lu,\"rx\":%d,\"rx_error\":%lu,"
        "\"flushed\":%d,\"flush_error\":%lu,\"armed\":%d,\"arm_stage\":%u,\"arm_error\":%lu,"
        "\"executed\":%d,\"result\":%llu,\"captured\":%d,\"exact_entry\":%d,"
        "\"stack_valid\":%u,\"restore_returned\":%d,\"bytes_equal\":%d,"
        "\"before_protection\":%lu,\"armed_protection\":%lu,\"final_protection\":%lu,\"memory_type\":%lu,",
        page!=NULL,(unsigned long)alloc_error,rx,(unsigned long)rx_error,flushed,(unsigned long)flush_error,
        armed,stage,(unsigned long)error,executed,(unsigned long long)result,captured,
        captured&&record.instruction==(uintptr_t)page,record.stack_valid,restored,bytes_equal,
        (unsigned long)before.Protect,(unsigned long)after_arm.Protect,(unsigned long)after.Protect,(unsigned long)before.Type);
    api_identity(f,"virtual_protect",(uintptr_t)&VirtualProtect);fputc(',',f);
    HMODULE ntdll=GetModuleHandleA("ntdll.dll");
    api_identity(f,"nt_protect_virtual_memory",ntdll?(uintptr_t)GetProcAddress(ntdll,"NtProtectVirtualMemory"):0);
    fputs("}\n",f);fclose(f);
    plugin->struct_size=sizeof *plugin;plugin->api_version=SNOW_PLUGIN_API_VERSION;
    plugin->name="execution_control";plugin->version="experimental-1";
    return 0;
}
