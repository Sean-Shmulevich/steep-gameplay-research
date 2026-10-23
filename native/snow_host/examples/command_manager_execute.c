/* Opt-in constructor-page execution experiment. Raw context stays private.
 * First execution anywhere on the page wins. No ownership/lifetime guarantee.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "snow_plugin.h"
#include "snow_first_execute.h"
#include "snow_local_protection.h"
static char output[MAX_PATH];
static uintptr_t base,target;
static volatile LONG cancelled;
static unsigned timeout_ms;
static int compatible,initial_read,armed;
static uint64_t initial;
static DWORD initial_protection;
static DWORD initial_type,initial_state,pin_error;
static uintptr_t initial_allocation;
static int eligible,pin_ok;
static int continuation_requested,backend_ready;
static SnowLocalProtection continuation;
static int prepare_trace(void){
    char path[MAX_PATH+16];snprintf(path,sizeof path,"%s.trace.bin",output);
    HANDLE file=CreateFileA(path,GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,
        NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    if(file==INVALID_HANDLE_VALUE)return 0;
    HANDLE mapping=CreateFileMappingA(file,NULL,PAGE_READWRITE,0,sizeof(SnowFirstExecuteTrace),NULL);
    CloseHandle(file);if(!mapping)return 0;
    SnowFirstExecuteTrace *view=MapViewOfFile(mapping,FILE_MAP_ALL_ACCESS,0,0,sizeof *view);
    CloseHandle(mapping);if(!view)return 0;
    if(!snow_first_execute_trace(view)){UnmapViewOfFile(view);return 0;}
    /* Retain the view until process exit, including failed arming. */
    return 1;
}
/* Flush initialization milestones outside the exception handler. A process exit
 * before the worker report must not erase which arming gates completed. */
static void milestone(const char *stage){
    char path[MAX_PATH+16];snprintf(path,sizeof path,"%s.stages.jsonl",output);
    FILE *f=fopen(path,"a");if(!f)return;
    unsigned arm_stage=0;DWORD arm_error=0;
    snow_first_execute_arm_diagnostic(&arm_stage,&arm_error);
    fprintf(f,"{\"stage\":\"%s\",\"compatible\":%d,\"eligible\":%d,"
        "\"backend_ready\":%d,\"armed\":%d,\"arm_stage\":%u,\"arm_error\":%lu,"
        "\"backend_calls\":%ld,\"backend_last_status\":\"%08lx\"}\n",
        stage,compatible,eligible,backend_ready,armed,arm_stage,(unsigned long)arm_error,
        InterlockedCompareExchange(&continuation.calls,0,0),
        (unsigned long)InterlockedCompareExchange(&continuation.last_status,0,0));
    fclose(f);
}
static int read_at(uintptr_t p,void *out,size_t n){SIZE_T got=0;return ReadProcessMemory(GetCurrentProcess(),(void *)p,out,n,&got)&&got==n;}
static int fingerprint(uintptr_t p,size_t n,uint64_t expected){
    unsigned char code[32];uint64_t h=UINT64_C(14695981039346656037);
    if(n>sizeof code || !read_at(p,code,n))return 0;
    for(size_t i=0;i<n;i++)h=(h^code[i])*UINT64_C(1099511628211);
    return h==expected;
}
static DWORD WINAPI collect(LPVOID unused){
    (void)unused;SnowFirstExecuteRecord r={0};int captured=0,restored=0;
    ULONGLONG end=GetTickCount64()+timeout_ms;
    if(armed){
        while(!(captured=snow_first_execute_read(&r)) && GetTickCount64()<end &&
              !InterlockedCompareExchange(&cancelled,0,0))Sleep(1);
        end=GetTickCount64()+2000;
        do{restored=snow_first_execute_cancel();if(restored)break;Sleep(1);}while(GetTickCount64()<end);
        captured=snow_first_execute_read(&r);
    }
    MEMORY_BASIC_INFORMATION info={0};int queried=VirtualQuery((void *)target,&info,sizeof info)!=0;
    uint64_t later=0;int later_read=read_at(base+0x312f3a8,&later,8);
    LARGE_INTEGER qpf;QueryPerformanceFrequency(&qpf);
    FILE *f=fopen(output,"w");if(!f)return 0;
    unsigned arm_stage=0;DWORD arm_error=0;snow_first_execute_arm_diagnostic(&arm_stage,&arm_error);
    fprintf(f,"{\"compatible\":%d,\"initial_read\":%d,\"initial_null\":%d,\"armed\":%d,"
        "\"captured\":%d,\"exact_constructor\":%d,\"restore_returned\":%d,\"page_query\":%d,"
        "\"initial_protection\":%lu,\"final_protection\":%lu,\"base\":\"%llx\",\"target\":\"%llx\","
        "\"instruction\":\"%llx\",\"fault_address\":\"%llx\",\"thread\":%lu,\"tick\":%llu,\"qpf\":%llu,"
        "\"later_read\":%d,\"later_manager\":\"%llx\",\"stack_valid\":%u,\"stack_hex\":\"",
        compatible,initial_read,initial_read&&initial==0,armed,captured,captured&&r.instruction==target,
        restored,queried,(unsigned long)initial_protection,(unsigned long)info.Protect,
        (unsigned long long)base,(unsigned long long)target,(unsigned long long)r.instruction,
        (unsigned long long)r.fault_address,(unsigned long)r.thread,(unsigned long long)r.tick,
        (unsigned long long)qpf.QuadPart,later_read,(unsigned long long)later,r.stack_valid);
    if(r.stack_valid)for(size_t i=0;i<sizeof r.stack;i++)fprintf(f,"%02x",r.stack[i]);
    fputs("\",\"registers\":{",f);
    const char *names[]={"rax","rbx","rcx","rdx","rsi","rdi","rbp","rsp","r8","r9","r10","r11","r12","r13","r14","r15","rip"};
    uint64_t values[]={r.context.Rax,r.context.Rbx,r.context.Rcx,r.context.Rdx,r.context.Rsi,r.context.Rdi,r.context.Rbp,r.context.Rsp,r.context.R8,r.context.R9,r.context.R10,r.context.R11,r.context.R12,r.context.R13,r.context.R14,r.context.R15,r.context.Rip};
    for(size_t i=0;i<17;i++)fprintf(f,"%s\"%s\":\"%llx\"",i?",":"",names[i],(unsigned long long)values[i]);
    fprintf(f,"},\"initial_type\":%lu,\"initial_state\":%lu,\"initial_allocation\":\"%llx\","
        "\"eligible\":%d,\"pin_ok\":%d,\"pin_error\":%lu,\"arm_stage\":%u,\"arm_error\":%lu,"
        "\"continuation_requested\":%d,\"backend_ready\":%d,\"continuation_joined\":%d,\"continuation_rechecked\":%d,"
        "\"backend_calls\":%ld,\"backend_last_status\":\"%08lx\"}\n",
        (unsigned long)initial_type,(unsigned long)initial_state,(unsigned long long)initial_allocation,
        eligible,pin_ok,(unsigned long)pin_error,arm_stage,(unsigned long)arm_error,
        continuation_requested,backend_ready,continuation.joined,continuation.rechecked,continuation.calls,
        (unsigned long)continuation.last_status);fclose(f);return 0;
}
static void unload(void *unused){(void)unused;InterlockedExchange(&cancelled,1);if(armed)snow_first_execute_cancel();}
__declspec(dllexport) int SnowMod_Initialize(const SnowHostApiV1 *api,SnowPluginV1 *plugin){
    if(!api || !plugin || api->api_version!=SNOW_PLUGIN_API_VERSION || api->struct_size<sizeof *api ||
       !api->config_path || strlen(api->config_path)+14>=MAX_PATH ||
       GetPrivateProfileIntA("execution","enabled",0,api->config_path)!=1)return 1;
    timeout_ms=GetPrivateProfileIntA("execution","timeout_ms",60000,api->config_path);
    if(timeout_ms<100 || timeout_ms>90000)return 1;
    char backend_name[24]={0};GetPrivateProfileStringA("execution","backend","virtualprotect",backend_name,sizeof backend_name,api->config_path);
    continuation_requested=!strcmp(backend_name,"continuation");
    if(!continuation_requested && strcmp(backend_name,"virtualprotect"))return 1;
    snprintf(output,sizeof output,"%s.execute.json",api->config_path);
    base=(uintptr_t)GetModuleHandleW(NULL);target=base+0x647650;
    compatible=fingerprint(base+0x674bb0,15,UINT64_C(0x914345ed589be986)) &&
        fingerprint(target,32,UINT64_C(0xb24d59629290bbbb));
    MEMORY_BASIC_INFORMATION info={0};HMODULE pinned;
    if(VirtualQuery((void *)target,&info,sizeof info)){
        initial_protection=info.Protect;initial_type=info.Type;initial_state=info.State;
        initial_allocation=(uintptr_t)info.AllocationBase;
    }
    eligible=compatible && (initial_read=read_at(base+0x312f3a8,&initial,8)) && initial==0 &&
       info.State==MEM_COMMIT && info.Type==MEM_IMAGE && info.AllocationBase==(void *)base && info.Protect==PAGE_EXECUTE_READ;
    milestone("eligibility_checked");
    if(eligible && GetPrivateProfileIntA("execution","trace",0,api->config_path)==1 && !prepare_trace()){
        milestone("trace_failed");collect(NULL);return 1;
    }
    if(eligible){
        pin_ok=GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)target,&pinned);
        if(!pin_ok)pin_error=GetLastError();
        else{
            backend_ready=!continuation_requested || (snow_local_protection_resolve(&continuation) &&
                snow_first_execute_backend(snow_local_protection_apply,&continuation));
            milestone("backend_checked");
            if(backend_ready)armed=snow_first_execute_arm((void *)target);
            milestone("arm_returned");
        }
    }
    if(!armed){collect(NULL);return 1;}
    plugin->struct_size=sizeof *plugin;plugin->api_version=SNOW_PLUGIN_API_VERSION;
    plugin->name="command_manager_execute";plugin->version="experimental-1";plugin->on_unload=unload;
    HANDLE worker=CreateThread(NULL,0,collect,NULL,0,NULL);
    if(!worker){snow_first_execute_cancel();return 1;}
    CloseHandle(worker);return 0;
}
