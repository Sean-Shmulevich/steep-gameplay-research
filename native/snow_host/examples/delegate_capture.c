/* Opt-in one-shot main-delegate observation. A controller creates the trigger
 * only inside its bounded gameplay/owner-lifetime experiment. No general owner
 * exclusion is supplied here. Output contains private process provenance.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "snow_plugin.h"
#include "snow_delegate_probe.h"
static char trigger[MAX_PATH],output[MAX_PATH];
static unsigned duration,request_id,request_count=1;
static SnowDelegateSite site=SNOW_DELEGATE_GRAPHICS_MAIN;
static const char *site_name="graphics";
static volatile LONG cancelled;
static int read_at(uint64_t address,void *dst,size_t n) {
    SIZE_T got=0;return ReadProcessMemory(GetCurrentProcess(),(void *)(uintptr_t)address,dst,n,&got)&&got==n;
}
static int signature(uint64_t base,uint32_t rva,size_t n,uint64_t expected) {
    unsigned char bytes[128];uint64_t h=UINT64_C(14695981039346656037);
    if(n>sizeof bytes || !read_at(base+rva,bytes,n))return 0;
    for(size_t i=0;i<n;i++)h=(h^bytes[i])*UINT64_C(1099511628211);
    return h==expected;
}
static void write_state(FILE *f,const SnowDelegateJobState *s) {
    fprintf(f,"{\"valid\":%u,\"executions\":%u,\"outstanding\":%d,\"state\":%u,"
        "\"started\":%u,\"requested\":%u,\"holds\":%u,\"usage\":%u,\"selector\":%u}",
        (unsigned)s->valid,(unsigned)s->executions,(int)s->outstanding,(unsigned)s->state,
        (unsigned)s->started,(unsigned)s->requested,(unsigned)s->holds,(unsigned)s->usage,(unsigned)s->selector);
}
static DWORD WINAPI capture(LPVOID unused) {
    (void)unused;ULONGLONG until=GetTickCount64()+180000;
    while(GetFileAttributesA(trigger)==INVALID_FILE_ATTRIBUTES) {
        if(InterlockedCompareExchange(&cancelled,0,0) || GetTickCount64()>=until)return 0;
        Sleep(10);
    }
    if(InterlockedCompareExchange(&cancelled,0,0))return 0;
    uint64_t base=(uintptr_t)GetModuleHandleW(NULL),owner=0,descriptor[4]={0};
    uint32_t function_rva=site==SNOW_DELEGATE_ENGINE_MAIN?0x656900:0x656c20;
    uint32_t descriptor_offset=site==SNOW_DELEGATE_ENGINE_MAIN?0x8d8:0x3b0;
    uint64_t function_hash=site==SNOW_DELEGATE_ENGINE_MAIN?
        UINT64_C(0x118b7155fb2e01ca):UINT64_C(0x17e686d0b8520ef0);
    int compatible=signature(base,0x8ab390,9,UINT64_C(0xc8597ed6f61359ff)) &&
        signature(base,0x65b1e0,116,UINT64_C(0xc69ce13c5cf9fd06)) &&
        signature(base,function_rva,32,function_hash);
    int configured=0,installed=0,restored=0,drained=0;
    size_t used=0,dropped=0;
    if(compatible && read_at(base+0x312cfe8,&owner,8) && owner>=0x10000 &&
       owner<UINT64_C(0x7fffffff0000) && read_at(owner+descriptor_offset,descriptor,sizeof descriptor) &&
       descriptor[0]==base+function_rva && descriptor[3]==base+0x8ab390 &&
       (descriptor[2]&~UINT64_C(3))==owner) {
        SnowDelegateBinding binding={base+0x312cfe8,owner,base+0x1e89618,base+0x65b1e0,
                                     descriptor[0],descriptor[1],descriptor[2],descriptor[3]};
        configured=SnowDelegateProbe_ConfigureSite(&binding,site);
    }
    SnowDelegateRequestObservation requests[16]={0};
    SnowObservationReceipt outcomes[16]={0};unsigned collected=0,submitted=0;
    SnowObservationAdmission last_submit=SNOW_OBSERVATION_INVALID,after_close=SNOW_OBSERVATION_INVALID;
    int request_armed=0;
    if(configured && request_id)request_armed=SnowDelegateProbe_ArmObservation(request_id);
    if(request_armed)submitted=1;
    if(configured && (!request_id || request_armed)) {
        installed=SnowDelegateProbe_Install();
        if(installed) {
            until=GetTickCount64()+duration;
            while(GetTickCount64()<until && !InterlockedCompareExchange(&cancelled,0,0)) {
                if(request_count>1 && collected<submitted) {
                    SnowObservationReceipt outcome=SnowDelegateProbe_CollectObservation(&requests[collected]);
                    if(outcome) {
                        outcomes[collected++]=outcome;
                        if(outcome==SNOW_OBSERVATION_RETURNED && submitted<request_count) {
                            last_submit=SnowDelegateProbe_SubmitObservation((uint64_t)request_id+submitted);
                            if(last_submit==SNOW_OBSERVATION_ACCEPTED)++submitted;
                        }
                    }
                }
                Sleep(1);
            }
        }
        restored=SnowDelegateProbe_Restore();
        until=GetTickCount64()+2000;
        do { drained=SnowDelegateProbe_Close(&used,&dropped);if(drained)break;Sleep(1); }while(GetTickCount64()<until);
    }
    if(request_count>1) {
        if(collected<submitted) {
            SnowObservationReceipt outcome=SnowDelegateProbe_CollectObservation(&requests[collected]);
            if(outcome)outcomes[collected++]=outcome;
        }
        after_close=SnowDelegateProbe_SubmitObservation((uint64_t)request_id+request_count+1);
        char repeat_output[MAX_PATH+32];snprintf(repeat_output,sizeof repeat_output,"%s.requests.json",output);
        FILE *rf=fopen(repeat_output,"w");
        if(rf) {
            fprintf(rf,"{\"route\":\"intercepted_engine_delegate\",\"requested\":%u,\"submitted\":%u,\"collected\":%u,\"last_submit\":%u,\"after_close\":%u,\"receipts\":[",
                request_count,submitted,collected,(unsigned)last_submit,(unsigned)after_close);
            for(unsigned i=0;i<collected;i++) {
                SnowDelegateRequestObservation *r=&requests[i];
                fprintf(rf,"%s{\"id\":%llu,\"outcome\":%u,\"entry\":%llu,\"exit\":%llu,\"thread\":%llu,\"caller\":\"%llx\",\"receiver\":\"%llx\",\"storage\":\"%llx\",\"manager_before\":\"%llx\",\"manager_after\":\"%llx\",\"valid_before\":%u,\"valid_after\":%u}",
                    i?",":"",(unsigned long long)r->request_id,(unsigned)outcomes[i],(unsigned long long)r->entry_tick,
                    (unsigned long long)r->exit_tick,(unsigned long long)r->thread,(unsigned long long)r->caller,
                    (unsigned long long)r->receiver,(unsigned long long)r->storage,(unsigned long long)r->manager_before,
                    (unsigned long long)r->manager_after,r->valid_before,r->valid_after);
            }
            fputs("]}\n",rf);fclose(rf);
        }
    }
    if(request_id && request_count==1) {
        char request_output[MAX_PATH+32];
        snprintf(request_output,sizeof request_output,"%s.request.json",output);
        FILE *rf=fopen(request_output,"w");
        SnowDelegateRequestObservation r={0};
        SnowObservationReceipt outcome=SnowDelegateProbe_CollectObservation(&r);
        int returned=outcome==SNOW_OBSERVATION_RETURNED;
        if(rf) {
            fprintf(rf,"{\"route\":\"intercepted_engine_delegate\",\"native_queue_submission\":false,"
                "\"request_id\":%u,\"armed\":%d,\"returned\":%d,\"outcome\":%u,\"entry\":%llu,\"exit\":%llu,"
                "\"thread\":%llu,\"caller\":\"%llx\",\"receiver\":\"%llx\",\"storage\":\"%llx\","
                "\"manager_before\":\"%llx\",\"manager_after\":\"%llx\",\"valid_before\":%u,\"valid_after\":%u}\n",
                request_id,request_armed,returned,(unsigned)outcome,(unsigned long long)r.entry_tick,(unsigned long long)r.exit_tick,
                (unsigned long long)r.thread,(unsigned long long)r.caller,(unsigned long long)r.receiver,
                (unsigned long long)r.storage,(unsigned long long)r.manager_before,(unsigned long long)r.manager_after,
                r.valid_before,r.valid_after);
            fclose(rf);
        }
    }
    FILE *f=fopen(output,"w");
    if(f) {
        LARGE_INTEGER frequency;QueryPerformanceFrequency(&frequency);
        fprintf(f,"{\"kind\":\"summary\",\"record_abi\":3,\"site\":\"%s\",\"compatible\":%d,\"configured\":%d,\"installed\":%d,\"restored\":%d,\"drained\":%d,\"used\":%llu,\"dropped\":%llu,\"qpf\":%llu,\"owner\":\"%llx\"}\n",
            site_name,compatible,configured,installed,restored,drained,(unsigned long long)used,
            (unsigned long long)dropped,(unsigned long long)frequency.QuadPart,(unsigned long long)owner);
        if(drained)for(size_t i=0;i<used;i++) {
            SnowDelegateRecord r;if(!SnowDelegateProbe_Read(i,&r,sizeof r))break;
            fprintf(f,"{\"kind\":\"record\",\"index\":%llu,\"storage\":\"%llx\",\"receiver\":\"%llx\",\"result\":\"%llx\",\"entry\":%llu,\"exit\":%llu,\"thread\":%llu,\"caller\":\"%llx\",\"before\":",
                (unsigned long long)i,(unsigned long long)r.function_storage,(unsigned long long)r.receiver,
                (unsigned long long)r.result,(unsigned long long)r.entry_tick,(unsigned long long)r.exit_tick,(unsigned long long)r.thread,(unsigned long long)r.caller);
            write_state(f,&r.before);fputs(",\"after\":",f);write_state(f,&r.after);fputs("}\n",f);
        }
        fclose(f);
    }
    return 0;
}
static void unload(void *unused) { (void)unused;InterlockedExchange(&cancelled,1); }
__declspec(dllexport) int SnowMod_Initialize(const SnowHostApiV1 *api,SnowPluginV1 *plugin) {
    HMODULE pinned;
    if(!api || !plugin || api->api_version!=SNOW_PLUGIN_API_VERSION ||
       api->struct_size<sizeof *api || !api->config_path ||
       GetPrivateProfileIntA("capture","enabled",0,api->config_path)!=1 ||
       strlen(api->config_path)+16>=MAX_PATH)return 1;
    char selected[32];
    GetPrivateProfileStringA("capture","site","graphics",selected,sizeof selected,api->config_path);
    if(!strcmp(selected,"engine")) { site=SNOW_DELEGATE_ENGINE_MAIN;site_name="engine"; }
    else if(!strcmp(selected,"graphics")) { site=SNOW_DELEGATE_GRAPHICS_MAIN;site_name="graphics"; }
    else return 1;
    request_id=GetPrivateProfileIntA("capture","request_id",0,api->config_path);
    request_count=GetPrivateProfileIntA("capture","request_count",1,api->config_path);
    if(!request_count || request_count>16 || (request_count>1 && !request_id))return 1;
    if(request_id && site!=SNOW_DELEGATE_ENGINE_MAIN)return 1;
    duration=GetPrivateProfileIntA("capture","milliseconds",500,api->config_path);
    if(duration<100 || duration>2000)return 1;
    snprintf(trigger,sizeof trigger,"%s.trigger",api->config_path);
    snprintf(output,sizeof output,"%s.trace.jsonl",api->config_path);
    /* Refuse stale triggers: initialization never silently starts a capture. */
    if(GetFileAttributesA(trigger)!=INVALID_FILE_ATTRIBUTES)return 1;
    if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
                          (LPCSTR)(uintptr_t)&capture,&pinned))return 1;
    plugin->struct_size=sizeof *plugin;plugin->api_version=SNOW_PLUGIN_API_VERSION;
    plugin->name="delegate_capture";plugin->version="experimental-1";plugin->on_unload=unload;
    HANDLE worker=CreateThread(NULL,0,capture,NULL,0,NULL);
    if(!worker)return 1;
    CloseHandle(worker);return 0;
}
