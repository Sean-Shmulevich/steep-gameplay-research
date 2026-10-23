/* Read-only, bounded API entry inspection. Raw bytes/addresses stay private.
 * Recognizes only entry E9, EB, FF25, 48FF25 and mov-rax/jmp-rax forwarding,
 * optionally after the exact eight-byte lea-rsp-self prefix seen in Wine.
 * No calls, conditional branches or general function bodies are traced. */
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
static void route(FILE *f,uintptr_t entry){
    uintptr_t seen[4]={0},address=entry;fputc('[',f);
    for(unsigned i=0;address && i<4;i++){
        seen[i]=address;unsigned char code[128]={0};int readable=read_at(address,code,sizeof code);
        uintptr_t next=0,slot=0;const char *kind="unrecognized_entry";int32_t d32;int8_t d8;
        const unsigned char lea_self[]={0x48,0x8d,0xa4,0x24,0,0,0,0};
        unsigned skip=readable&&!memcmp(code,lea_self,sizeof lea_self)?8:0;
        const unsigned char *op=code+skip;uintptr_t origin=address+skip;
        if(readable){
            if(op[0]==0xe9){memcpy(&d32,op+1,4);next=origin+5+(intptr_t)d32;kind="jmp_rel32";}
            else if(op[0]==0xeb){memcpy(&d8,op+1,1);next=origin+2+(intptr_t)d8;kind="jmp_rel8";}
            else if((op[0]==0xff && op[1]==0x25) || (op[0]==0x48 && op[1]==0xff && op[2]==0x25)){
                unsigned prefix=op[0]==0x48;memcpy(&d32,op+2+prefix,4);slot=origin+6+prefix+(intptr_t)d32;
                if(read_at(slot,&next,8))kind="jmp_rip_indirect";
                else{next=0;kind="unreadable_indirect_slot";}
            }else if(op[0]==0x48 && op[1]==0xb8 && op[10]==0xff && op[11]==0xe0){
                memcpy(&next,op+2,8);kind="mov_rax_jmp_rax";
            }
        }
        int repeated=0;for(unsigned j=0;j<=i;j++)if(next && next==seen[j])repeated=1;
        MEMORY_BASIC_INFORMATION info={0};VirtualQuery((void *)address,&info,sizeof info);
        HMODULE module=NULL;char path[MAX_PATH]={0};
        int module_ok=GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
            (LPCSTR)address,&module);
        if(module_ok)GetModuleFileNameA(module,path,sizeof path);
        path[sizeof path-1]=0;
        const char *name=strrchr(path,'\\');name=name?name+1:path;
        fprintf(f,"%s{\"address\":\"%llx\",\"read\":%d,\"module_ok\":%d,\"module\":\"",i?",":"",
            (unsigned long long)address,readable,module_ok);
        for(const char *p=name;*p;p++)if(*p>=32 && *p<127 && *p!='"' && *p!='\\')fputc(*p,f);
        fprintf(f,"\",\"module_offset\":\"%llx\",\"protection\":%lu,\"type\":%lu,\"code_hex\":\"",
            (unsigned long long)(module_ok?address-(uintptr_t)module:0),(unsigned long)info.Protect,(unsigned long)info.Type);
        if(readable)for(size_t j=0;j<sizeof code;j++)fprintf(f,"%02x",code[j]);
        fprintf(f,"\",\"kind\":\"%s\",\"prefix_bytes\":%u,\"slot\":\"%llx\",\"next\":\"%llx\",\"cycle\":%d,\"limit\":%d}",
            kind,skip,(unsigned long long)slot,(unsigned long long)next,repeated,i==3&&next!=0);
        if(repeated || !readable)break;
        address=next;
    }
    fputc(']',f);
}
__declspec(dllexport) int SnowMod_Initialize(const SnowHostApiV1 *api,SnowPluginV1 *plugin){
    if(!api || !plugin || api->api_version!=SNOW_PLUGIN_API_VERSION || api->struct_size<sizeof *api ||
       !api->config_path || strlen(api->config_path)+10>=MAX_PATH ||
       GetPrivateProfileIntA("snapshot","enabled",0,api->config_path)!=1)return 1;
    char output[MAX_PATH];snprintf(output,sizeof output,"%s.api.json",api->config_path);
    FILE *f=fopen(output,"w");if(!f)return 1;
    const char *modules[]={"kernel32.dll","kernel32.dll","kernelbase.dll","kernelbase.dll","ntdll.dll","ntdll.dll"};
    const char *names[]={"VirtualProtect","VirtualProtectEx","VirtualProtect","VirtualProtectEx","NtProtectVirtualMemory","ZwProtectVirtualMemory"};
    fputs("{\"entries\":[",f);
    for(unsigned i=0;i<6;i++){
        HMODULE m=GetModuleHandleA(modules[i]);uintptr_t entry=m?(uintptr_t)GetProcAddress(m,names[i]):0;
        fprintf(f,"%s{\"requested_module\":\"%s\",\"symbol\":\"%s\",\"resolved\":%d,\"route\":",i?",":"",modules[i],names[i],entry!=0);
        route(f,entry);fputc('}',f);
    }
    fputs("]}\n",f);fclose(f);
    plugin->struct_size=sizeof *plugin;plugin->api_version=SNOW_PLUGIN_API_VERSION;
    plugin->name="protection_api_snapshot";plugin->version="experimental-1";return 0;
}
