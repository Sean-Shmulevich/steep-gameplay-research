/* Opt-in one-shot paired graphics main/finalizer observation. A controller creates the trigger
 * only inside its bounded gameplay/owner-lifetime experiment. No general owner
 * exclusion is supplied here. Output contains private process provenance.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "snow_plugin.h"
#include "snow_finalizer_probe.h"
#include "snow_delegate_probe.h"
static char trigger[MAX_PATH],main_output[MAX_PATH],final_output[MAX_PATH];
typedef struct { int configured,installed,restored,drained;size_t used,dropped; } Outcome;
static uint64_t ticks(void) { LARGE_INTEGER q;QueryPerformanceCounter(&q);return q.QuadPart; }
static unsigned duration;
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
static void write_capture(const char *output,unsigned abi,const char *probe,int compatible,
    uint64_t owner,uint64_t start,uint64_t end,const Outcome *o,int (*read_record)(size_t,void *,size_t)) {
    FILE *f=fopen(output,"w");
    if(f) {
        LARGE_INTEGER frequency;QueryPerformanceFrequency(&frequency);
        fprintf(f,"{\"kind\":\"summary\",\"record_abi\":%u,\"probe\":\"%s\",\"joint_start_tick\":%llu,\"joint_end_tick\":%llu,\"compatible\":%d,\"configured\":%d,\"installed\":%d,\"restored\":%d,\"drained\":%d,\"used\":%llu,\"dropped\":%llu,\"qpf\":%llu,\"owner\":\"%llx\"}\n",
            abi,probe,(unsigned long long)start,(unsigned long long)end,compatible,o->configured,o->installed,o->restored,o->drained,(unsigned long long)o->used,
            (unsigned long long)o->dropped,(unsigned long long)frequency.QuadPart,(unsigned long long)owner);
        if(o->drained)for(size_t i=0;i<o->used;i++) {
            SnowDelegateRecord r;if(!read_record(i,&r,sizeof r))break;
            fprintf(f,"{\"kind\":\"record\",\"index\":%llu,\"storage\":\"%llx\",\"receiver\":\"%llx\",\"result\":\"%llx\",\"entry\":%llu,\"exit\":%llu,\"thread\":%llu,\"caller\":\"%llx\",\"before\":",
                (unsigned long long)i,(unsigned long long)r.function_storage,(unsigned long long)r.receiver,
                (unsigned long long)r.result,(unsigned long long)r.entry_tick,(unsigned long long)r.exit_tick,(unsigned long long)r.thread,(unsigned long long)r.caller);
            write_state(f,&r.before);fputs(",\"after\":",f);write_state(f,&r.after);fputs("}\n",f);
        }
        fclose(f);
    }
}
static DWORD WINAPI capture(LPVOID unused) {
    (void)unused;ULONGLONG until=GetTickCount64()+180000;
    while(GetFileAttributesA(trigger)==INVALID_FILE_ATTRIBUTES) {
        if(InterlockedCompareExchange(&cancelled,0,0)||GetTickCount64()>=until)return 0;
        Sleep(10);
    }
    if(InterlockedCompareExchange(&cancelled,0,0))return 0;
    uint64_t base=(uintptr_t)GetModuleHandleW(NULL),owner=0,table=0,target=0,d[4]={0};
    uint64_t start=0,end=0;Outcome m={0},f={0};
    int compatible=signature(base,0x11d1670,123,UINT64_C(0x328981937b90e00a)) &&
        signature(base,0x11e2d70,128,UINT64_C(0xda3f682f701346f6)) &&
        signature(base,0x65b1e0,116,UINT64_C(0xc69ce13c5cf9fd06)) &&
        signature(base,0x8ab390,9,UINT64_C(0xc8597ed6f61359ff)) &&
        signature(base,0x656c20,32,UINT64_C(0x17e686d0b8520ef0));
    if(compatible&&read_at(base+0x312cfe8,&owner,8)&&owner>=0x10000&&owner<UINT64_C(0x7fffffff0000)&&
       read_at(owner+0x218,&table,8)&&table==base+0x1e89618&&
       read_at(table+0x70,&target,8)&&target==base+0x11d1670&&
       read_at(owner+0x3b0,d,sizeof d)&&d[0]==base+0x656c20&&d[3]==base+0x8ab390&&
       (d[2]&~UINT64_C(3))==owner) {
        SnowDelegateBinding mb={base+0x312cfe8,owner,table,base+0x65b1e0,d[0],d[1],d[2],d[3]};
        SnowFinalizerBinding fb={base+0x312cfe8,owner,table,target};
        m.configured=SnowDelegateProbe_Configure(&mb);
        f.configured=SnowFinalizerProbe_Configure(&fb);
    }
    if(m.configured&&f.configured) {
        m.installed=SnowDelegateProbe_Install();
        if(m.installed==1)f.installed=SnowFinalizerProbe_Install();
        if(m.installed==1&&f.installed==1) {
            start=ticks();until=GetTickCount64()+duration;
            while(GetTickCount64()<until&&!InterlockedCompareExchange(&cancelled,0,0))Sleep(1);
            end=ticks();
        }
    }
    /* Restore every configured adapter, including partial/failed installation. */
    if(f.configured)f.restored=SnowFinalizerProbe_Restore();
    if(m.configured)m.restored=SnowDelegateProbe_Restore();
    until=GetTickCount64()+2000;
    do {
        if(m.configured&&!m.drained)m.drained=SnowDelegateProbe_Close(&m.used,&m.dropped);
        if(f.configured&&!f.drained)f.drained=SnowFinalizerProbe_Close(&f.used,&f.dropped);
        if((!m.configured||m.drained)&&(!f.configured||f.drained))break;
        Sleep(1);
    }while(GetTickCount64()<until);
    write_capture(main_output,3,"main",compatible,owner,start,end,&m,SnowDelegateProbe_Read);
    write_capture(final_output,1,"finalizer",compatible,owner,start,end,&f,SnowFinalizerProbe_Read);
    return 0;
}
static void unload(void *unused) { (void)unused;InterlockedExchange(&cancelled,1); }
__declspec(dllexport) int SnowMod_Initialize(const SnowHostApiV1 *api,SnowPluginV1 *plugin) {
    HMODULE pinned;
    if(!api || !plugin || api->api_version!=SNOW_PLUGIN_API_VERSION ||
       api->struct_size<sizeof *api || !api->config_path ||
       GetPrivateProfileIntA("capture","enabled",0,api->config_path)!=1 ||
       strlen(api->config_path)+32>=MAX_PATH)return 1;
    duration=GetPrivateProfileIntA("capture","milliseconds",500,api->config_path);
    if(duration<100 || duration>2000)return 1;
    snprintf(trigger,sizeof trigger,"%s.trigger",api->config_path);
    snprintf(main_output,sizeof main_output,"%s.main.trace.jsonl",api->config_path);
    snprintf(final_output,sizeof final_output,"%s.finalizer.trace.jsonl",api->config_path);
    /* Refuse stale triggers: initialization never silently starts a capture. */
    if(GetFileAttributesA(trigger)!=INVALID_FILE_ATTRIBUTES ||
       GetFileAttributesA(main_output)!=INVALID_FILE_ATTRIBUTES ||
       GetFileAttributesA(final_output)!=INVALID_FILE_ATTRIBUTES)return 1;
    if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
                          (LPCSTR)(uintptr_t)&capture,&pinned))return 1;
    plugin->struct_size=sizeof *plugin;plugin->api_version=SNOW_PLUGIN_API_VERSION;
    plugin->name="scheduler_phase_capture";plugin->version="experimental-1";plugin->on_unload=unload;
    HANDLE worker=CreateThread(NULL,0,capture,NULL,0,NULL);
    if(!worker)return 1;
    CloseHandle(worker);return 0;
}
