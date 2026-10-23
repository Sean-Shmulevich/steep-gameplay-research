/* One-shot read-only observation during plugin initialization. No hook, worker,
 * native engine call or manager mutation. Output contains private provenance.
 * Sequential reads do not establish ownership, atomicity or publication time.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "snow_plugin.h"
static int read_at(uint64_t address,void *out,size_t size){
    SIZE_T got=0;
    return ReadProcessMemory(GetCurrentProcess(),(void *)(uintptr_t)address,out,size,&got)&&got==size;
}
__declspec(dllexport) int SnowMod_Initialize(const SnowHostApiV1 *api,SnowPluginV1 *plugin){
    if(!api || !plugin || api->api_version!=SNOW_PLUGIN_API_VERSION ||
       api->struct_size<sizeof *api || !api->config_path ||
       strlen(api->config_path)+18>=MAX_PATH ||
       GetPrivateProfileIntA("observation","enabled",0,api->config_path)!=1)return 1;
    uint64_t base=(uintptr_t)GetModuleHandleW(NULL),manager=0,again=0,lock=0,array=0;
    unsigned char code[15];uint64_t hash=UINT64_C(14695981039346656037);
    LARGE_INTEGER begin,end,frequency;QueryPerformanceCounter(&begin);QueryPerformanceFrequency(&frequency);
    int compatible=read_at(base+0x674bb0,code,sizeof code);
    if(compatible){for(size_t i=0;i<sizeof code;i++)hash=(hash^code[i])*UINT64_C(1099511628211);
        compatible=hash==UINT64_C(0x914345ed589be986);}
    uint32_t count=0,capacity=0;int owner_read=0,fields_read=0,recheck=0;
    if(compatible){
        owner_read=read_at(base+0x312f3a8,&manager,8);
        if(owner_read && manager>=0x10000 && manager<UINT64_C(0x7fffffff0000))
            fields_read=read_at(manager,&lock,8) && read_at(manager+0x30,&array,8) &&
                read_at(manager+0x38,&count,4) && read_at(manager+0x44,&capacity,4);
        recheck=read_at(base+0x312f3a8,&again,8);
    }
    QueryPerformanceCounter(&end);
    FILETIME created,exited,kernel,user;ULARGE_INTEGER creation={0};
    int identity=GetProcessTimes(GetCurrentProcess(),&created,&exited,&kernel,&user);
    if(identity){creation.LowPart=created.dwLowDateTime;creation.HighPart=created.dwHighDateTime;}
    char path[MAX_PATH];snprintf(path,sizeof path,"%s.observation.json",api->config_path);
    FILE *f=fopen(path,"w");if(!f)return 1;
    fprintf(f,"{\"kind\":\"command_manager_plugin_initialization\",\"pid\":%lu,"
        "\"process_identity_valid\":%d,\"creation_filetime\":%llu,"
        "\"qpf\":%llu,\"entry_tick\":%llu,\"exit_tick\":%llu,"
        "\"compatible\":%d,\"owner_read\":%d,\"fields_read\":%d,\"recheck_read\":%d,"
        "\"same_pointer\":%d,\"manager\":\"%llx\",\"lock\":\"%llx\",\"array\":\"%llx\","
        "\"count\":%u,\"capacity\":%u,\"lifetime_proved\":false}\n",
        (unsigned long)GetCurrentProcessId(),identity,(unsigned long long)creation.QuadPart,
        (unsigned long long)frequency.QuadPart,(unsigned long long)begin.QuadPart,
        (unsigned long long)end.QuadPart,compatible,owner_read,fields_read,recheck,
        owner_read&&recheck&&manager==again,(unsigned long long)manager,
        (unsigned long long)lock,(unsigned long long)array,count,capacity);
    if(fclose(f))return 1;
    plugin->struct_size=sizeof *plugin;plugin->api_version=SNOW_PLUGIN_API_VERSION;
    plugin->name="command_manager_startup";plugin->version="experimental-1";
    return 0;
}
