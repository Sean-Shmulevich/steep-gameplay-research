/* Opt-in one-shot startup page-write experiment. Raw output is private.
 * Neighboring writes may win. This is not a lifetime pin or a mod command API.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "snow_plugin.h"
#include "snow_first_write.h"
static char output[MAX_PATH];
static uintptr_t base,target;
static volatile LONG cancelled;
static unsigned timeout_ms;
static int compatible,initial_read,armed;
static uint64_t initial;
static DWORD initial_protection;
static int read_at(uintptr_t p,void *out,size_t n){SIZE_T got=0;return ReadProcessMemory(GetCurrentProcess(),(void *)p,out,n,&got)&&got==n;}
static DWORD WINAPI collect(LPVOID unused){
    (void)unused;SnowFirstWriteRecord r={0};int captured=0,restored=0;
    ULONGLONG end=GetTickCount64()+timeout_ms;
    if(armed){
        while(!(captured=snow_first_write_read(&r)) && GetTickCount64()<end &&
              !InterlockedCompareExchange(&cancelled,0,0))Sleep(1);
        end=GetTickCount64()+2000;
        do{restored=snow_first_write_cancel();if(restored)break;Sleep(1);}while(GetTickCount64()<end);
        captured=snow_first_write_read(&r);
    }
    MEMORY_BASIC_INFORMATION page_info={0},code_info={0};
    int queried=VirtualQuery((void *)target,&page_info,sizeof page_info)!=0;
    uint64_t later=0;int later_read=read_at(target,&later,8);
    unsigned char code[32]={0};int code_read=captured && read_at(r.instruction,code,sizeof code);
    if(captured)VirtualQuery((void *)r.instruction,&code_info,sizeof code_info);
    LARGE_INTEGER qpf;QueryPerformanceFrequency(&qpf);
    FILE *f=fopen(output,"w");if(!f)return 0;
    fprintf(f,"{\"compatible\":%d,\"initial_read\":%d,\"initial_null\":%d,\"armed\":%d,"
        "\"captured\":%d,\"restore_returned\":%d,\"page_query\":%d,\"initial_protection\":%lu,\"final_protection\":%lu,"
        "\"later_read\":%d,\"later_manager\":\"%llx\",\"target\":\"%llx\",\"fault_address\":\"%llx\","
        "\"instruction\":\"%llx\",\"instruction_allocation\":\"%llx\",\"instruction_type\":%lu,"
        "\"thread\":%lu,\"tick\":%llu,\"qpf\":%llu,\"code_read\":%d,\"code_hex\":\"",
        compatible,initial_read,initial_read&&initial==0,armed,captured,restored,queried,
        (unsigned long)initial_protection,(unsigned long)page_info.Protect,later_read,
        (unsigned long long)later,(unsigned long long)target,(unsigned long long)r.fault_address,
        (unsigned long long)r.instruction,(unsigned long long)(uintptr_t)code_info.AllocationBase,
        (unsigned long)code_info.Type,(unsigned long)r.thread,(unsigned long long)r.tick,
        (unsigned long long)qpf.QuadPart,code_read);
    if(code_read)for(size_t i=0;i<sizeof code;i++)fprintf(f,"%02x",code[i]);
    fputs("\",\"registers\":{",f);
    const char *names[]={"rax","rbx","rcx","rdx","rsi","rdi","rbp","rsp","r8","r9","r10","r11","r12","r13","r14","r15","rip"};
    uint64_t values[]={r.context.Rax,r.context.Rbx,r.context.Rcx,r.context.Rdx,r.context.Rsi,r.context.Rdi,r.context.Rbp,r.context.Rsp,r.context.R8,r.context.R9,r.context.R10,r.context.R11,r.context.R12,r.context.R13,r.context.R14,r.context.R15,r.context.Rip};
    for(size_t i=0;i<17;i++)fprintf(f,"%s\"%s\":\"%llx\"",i?",":"",names[i],(unsigned long long)values[i]);
    fputs("},\"windows\":[",f);
    for(uint32_t i=0;i<r.window_count;i++){
        SnowWriteWindow *w=&r.windows[i];
        fprintf(f,"%s{\"address\":\"%llx\",\"size\":%u,\"valid\":%u,\"hex\":\"",i?",":"",(unsigned long long)w->address,w->size,w->valid);
        if(w->valid)for(uint32_t j=0;j<w->size;j++)fprintf(f,"%02x",w->bytes[j]);
        fputs("\"}",f);
    }
    fputs("]}\n",f);fclose(f);return 0;
}
static void unload(void *unused){(void)unused;InterlockedExchange(&cancelled,1);if(armed)snow_first_write_cancel();}
__declspec(dllexport) int SnowMod_Initialize(const SnowHostApiV1 *api,SnowPluginV1 *plugin){
    if(!api || !plugin || api->api_version!=SNOW_PLUGIN_API_VERSION || api->struct_size<sizeof *api ||
       !api->config_path || strlen(api->config_path)+12>=MAX_PATH ||
       GetPrivateProfileIntA("publication","enabled",0,api->config_path)!=1)return 1;
    timeout_ms=GetPrivateProfileIntA("publication","timeout_ms",60000,api->config_path);
    if(timeout_ms<100 || timeout_ms>90000)return 1;
    snprintf(output,sizeof output,"%s.write.json",api->config_path);
    base=(uintptr_t)GetModuleHandleW(NULL);target=base+0x312f3a8;
    unsigned char code[15];uint64_t hash=UINT64_C(14695981039346656037);
    compatible=read_at(base+0x674bb0,code,sizeof code);
    if(compatible){for(size_t i=0;i<sizeof code;i++)hash=(hash^code[i])*UINT64_C(1099511628211);compatible=hash==UINT64_C(0x914345ed589be986);}
    MEMORY_BASIC_INFORMATION info={0};HMODULE pinned;
    if(compatible && (initial_read=read_at(target,&initial,8)) && initial==0 &&
       VirtualQuery((void *)target,&info,sizeof info) && info.Type==MEM_IMAGE &&
       info.AllocationBase==(void *)base && (info.Protect==PAGE_READWRITE || info.Protect==PAGE_WRITECOPY) &&
       GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)target,&pinned)){
        initial_protection=info.Protect;
        SnowWriteWindowSpec windows[]={{SNOW_WRITE_RBP,-16,64},{SNOW_WRITE_RBX,-16,32},{SNOW_WRITE_RSP,0,128}};
        if(snow_first_write_windows(windows,3))armed=snow_first_write_arm((void *)target);
    }
    if(!armed){collect(NULL);return 1;}
    plugin->struct_size=sizeof *plugin;plugin->api_version=SNOW_PLUGIN_API_VERSION;
    plugin->name="command_manager_write";plugin->version="experimental-1";plugin->on_unload=unload;
    HANDLE worker=CreateThread(NULL,0,collect,NULL,0,NULL);
    if(!worker){snow_first_write_cancel();return 1;}
    CloseHandle(worker);return 0;
}
