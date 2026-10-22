/* Opt-in, one-shot observation plugin. Build with the public Steep adapter and
 * probe sources. Disabled unless [capture] enabled=1 in its plugin .ini.
 * Pause acquires/configures. Resume installs for 1..5 seconds, then restores,
 * closes and drains. No velocity or pose setter is invoked. Output is local
 * JSONL; it contains process pointers and must not be committed as research.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "snow_plugin.h"
#include "snow_update_probe.h"
#include "steep_probe_binding.h"
static const SnowHostApiV1 *host;
static volatile LONG phase;
static unsigned milliseconds;
static char output[MAX_PATH];
static void number(FILE *f,float v) { if(isfinite(v)) fprintf(f,"%.9g",v); else fputs("null",f); }
static void floats(FILE *f,const float *v,unsigned n) {
    fputc('[',f); for(unsigned i=0;i<n;i++) { if(i) fputc(',',f); number(f,v[i]); } fputc(']',f);
}
static void sample(FILE *f,const SnowUpdateSnapshot *s) {
    fprintf(f,"{\"valid\":%u,\"runtime\":\"%llx\",\"main\":\"%llx\",\"rider\":\"%llx\",\"request\":%llu,\"substep\":%llu,\"gates\":[%u,%u,%u,%u],\"pending\":",
      s->valid,(unsigned long long)s->runtime,(unsigned long long)s->main_body,(unsigned long long)s->rider_body,
      (unsigned long long)s->request,(unsigned long long)s->substep,s->gates[0],s->gates[1],s->gates[2],s->gates[3]);
    floats(f,s->pending,4);
    fprintf(f,",\"preconsume_counter\":%d,\"preconsume_timers\":",(int)s->preconsume_counter);
    floats(f,s->preconsume_timers,2); fputs(",\"main_linear\":",f); floats(f,s->linear[0],3);
    fputs(",\"rider_linear\":",f); floats(f,s->linear[1],3);
    fputs(",\"main_angular\":",f); floats(f,s->angular[0],3);
    fputs(",\"rider_angular\":",f); floats(f,s->angular[1],3);
    fputs(",\"inverse_mass\":",f); floats(f,s->inverse_mass,2); fputc('}',f);
}
static DWORD WINAPI capture(LPVOID ignored) {
    (void)ignored;
    int installed=SnowProbe_InstallSlot();
    if(installed==1) Sleep(milliseconds);
    int restored=SnowProbe_RestoreSlot();
    size_t used=0,dropped=0; int drained=0;
    ULONGLONG until=GetTickCount64()+2000;
    do { drained=SnowProbe_Close(&used,&dropped); if(drained) break; Sleep(1); } while(GetTickCount64()<until);
    FILE *f=fopen(output,"w");
    if(f) {
        SnowProbeDispatchCounts counts={0};
        int counts_valid=SnowProbe_ReadDispatchCounts(&counts);
        LARGE_INTEGER frequency; QueryPerformanceFrequency(&frequency);
        fprintf(f,"{\"kind\":\"summary\",\"installed\":%d,\"restored\":%d,\"drained\":%d,\"records\":%llu,\"dropped\":%llu,\"qpf\":%llu,\"substep_available\":false,\"dispatch_counts_valid\":%d,\"selected_calls\":%llu,\"other_calls\":%llu}\n",
          installed,restored,drained,(unsigned long long)used,(unsigned long long)dropped,(unsigned long long)frequency.QuadPart,counts_valid,(unsigned long long)counts.selected_calls,(unsigned long long)counts.other_calls);
        if(drained) for(size_t i=0;i<used;i++) {
            SnowUpdateRecord r; if(!SnowProbe_ReadRecord(i,&r)) break;
            fprintf(f,"{\"kind\":\"record\",\"index\":%llu,\"actor\":\"%llx\",\"thread\":%llu,\"entry\":%llu,\"exit\":%llu,\"elapsed\":",
              (unsigned long long)i,(unsigned long long)r.actor,(unsigned long long)r.thread,
              (unsigned long long)r.entry_tick,(unsigned long long)r.exit_tick);
            number(f,r.elapsed); fputs(",\"derivative\":",f); number(f,r.derivative);
            fputs(",\"before\":",f); sample(f,&r.before); fputs(",\"after\":",f); sample(f,&r.after); fputs("}\n",f);
        }
        fclose(f);
    }
    InterlockedExchange(&phase,3); return 0;
}
static int paused(void *user) {
    (void)user;
    if(InterlockedCompareExchange(&phase,1,0)!=0) return 0;
    SnowUpdateBinding binding; SnowUpdateOriginal original; char why[256];
    if(snow_steep_probe_binding(&binding,&original,why,sizeof why)) {
        host->log(host->context,why); InterlockedExchange(&phase,0); return 0;
    }
    if(!SnowProbe_Configure(&binding,original)) {
        host->log(host->context,"capture configuration refused"); InterlockedExchange(&phase,3); return 0;
    }
    host->log(host->context,"capture configured; resume starts bounded observation"); return 0;
}
static int resumed(void *user,SnowResumeReason reason) {
    (void)user; (void)reason;
    if(InterlockedCompareExchange(&phase,2,1)!=1) return 0;
    HANDLE worker=CreateThread(NULL,0,capture,NULL,0,NULL);
    if(worker) CloseHandle(worker);
    else { SnowProbe_Close(NULL,NULL); InterlockedExchange(&phase,3); host->log(host->context,"capture worker creation failed"); }
    return 0;
}
__declspec(dllexport) int SnowMod_Initialize(const SnowHostApiV1 *api,SnowPluginV1 *plugin) {
    if(!api || !plugin || api->api_version!=SNOW_PLUGIN_API_VERSION || api->struct_size<sizeof *api || !api->config_path) return 1;
    if(GetPrivateProfileIntA("capture","enabled",0,api->config_path)!=1) return 1;
    unsigned seconds=GetPrivateProfileIntA("capture","seconds",2,api->config_path);
    if(seconds<1 || seconds>5 || strlen(api->config_path)+12>=sizeof output) return 1;
    snprintf(output,sizeof output,"%s.trace.jsonl",api->config_path);
    host=api; milliseconds=seconds*1000;
    plugin->struct_size=sizeof *plugin; plugin->api_version=SNOW_PLUGIN_API_VERSION;
    plugin->name="update_capture"; plugin->version="experimental-2";
    plugin->on_pause=paused; plugin->on_resume=resumed;
    return 0;
}
