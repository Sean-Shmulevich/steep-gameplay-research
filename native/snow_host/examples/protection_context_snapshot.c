/* Build-specific read-only snapshots for the redirected protection routine.
 * Raw pointer/payload output is private. Pointer rereads are not lifetime pins. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "snow_plugin.h"
static int read_at(uintptr_t address,void *out,SIZE_T size){
    MEMORY_BASIC_INFORMATION info;SIZE_T got=0;
    if(address<0x10000 || address>UINT64_C(0x7fffffffffff)-size ||
       !VirtualQuery((void *)address,&info,sizeof info) || info.State!=MEM_COMMIT ||
       (info.Protect&(PAGE_GUARD|PAGE_NOACCESS)) ||
       size>info.RegionSize-(address-(uintptr_t)info.BaseAddress))return 0;
    return ReadProcessMemory(GetCurrentProcess(),(void *)address,out,size,&got)&&got==size;
}
static void window(FILE *f,const char *label,uintptr_t address){
    unsigned char bytes[256]={0};MEMORY_BASIC_INFORMATION info={0};
    int ok=read_at(address,bytes,sizeof bytes);VirtualQuery((void *)address,&info,sizeof info);
    fprintf(f,"{\"label\":\"%s\",\"address\":\"%llx\",\"read\":%d,\"type\":%lu,"
        "\"protection\":%lu,\"allocation\":\"%llx\",\"hex\":\"",label,(unsigned long long)address,ok,
        (unsigned long)info.Type,(unsigned long)info.Protect,(unsigned long long)(uintptr_t)info.AllocationBase);
    if(ok)for(unsigned i=0;i<sizeof bytes;i++)fprintf(f,"%02x",bytes[i]);
    fputs("\"}",f);
}
__declspec(dllexport) int SnowMod_Initialize(const SnowHostApiV1 *api,SnowPluginV1 *plugin){
    if(!api || !plugin || api->api_version!=SNOW_PLUGIN_API_VERSION || api->struct_size<sizeof *api ||
       !api->config_path || strlen(api->config_path)+14>=MAX_PATH ||
       GetPrivateProfileIntA("context","enabled",0,api->config_path)!=1)return 1;
    uintptr_t base=(uintptr_t)GetModuleHandleW(NULL);unsigned char code[32]={0};
    uint64_t hash=UINT64_C(14695981039346656037),first=0,last=0;
    int compatible=read_at(base+0x4122688,code,sizeof code);
    if(compatible){for(unsigned i=0;i<sizeof code;i++)hash=(hash^code[i])*UINT64_C(1099511628211);compatible=hash==UINT64_C(0x1456172a4e7c2ca7);}
    char output[MAX_PATH];snprintf(output,sizeof output,"%s.context.json",api->config_path);
    FILE *f=fopen(output,"w");if(!f)return 1;
    int first_read=compatible&&read_at(base+0x3595838,&first,8),last_read=0;
    fprintf(f,"{\"compatible\":%d,\"base\":\"%llx\",\"first_read\":%d,\"context\":\"%llx\",\"windows\":[",
        compatible,(unsigned long long)base,first_read,(unsigned long long)first);
    if(compatible){
        window(f,"context",(uintptr_t)first);fputc(',',f);
        window(f,"initial_stream",base+0x34b8700);fputc(',',f);
        window(f,"scanned_image_window",base+0x3509400);
        if(GetPrivateProfileIntA("context","follow_candidate",0,api->config_path)==1){
            uint64_t candidate=0;
            if(first_read && first>=0x10000 && first<=UINT64_C(0x7fffffffffff)-0x80 &&
               read_at((uintptr_t)first+0x78,&candidate,8)){
                fputc(',',f);window(f,"context_plus_78_target",(uintptr_t)candidate);
            }
        }
        last_read=read_at(base+0x3595838,&last,8);
    }
    fprintf(f,"],\"last_read\":%d,\"context_after\":\"%llx\",\"pointer_equal\":%d}\n",
        last_read,(unsigned long long)last,first_read&&last_read&&first==last);fclose(f);
    plugin->struct_size=sizeof *plugin;plugin->api_version=SNOW_PLUGIN_API_VERSION;
    plugin->name="protection_context_snapshot";plugin->version="experimental-1";return 0;
}
