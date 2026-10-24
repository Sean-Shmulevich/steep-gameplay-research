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
static int attribute_jobs, observe_motion, observe_points;
static char output[MAX_PATH];
static void number(FILE *f,float v) { if(isfinite(v)) fprintf(f,"%.9g",v); else fputs("null",f); }
static void floats(FILE *f,const float *v,unsigned n) {
    fputc('[',f); for(unsigned i=0;i<n;i++) { if(i) fputc(',',f); number(f,v[i]); } fputc(']',f);
}
static void words(FILE *,const uint32_t *,unsigned);
static void point_sample(FILE *f,const SnowPointInputs *p) {
    fprintf(f,"{\"flags\":%u,\"kind\":%u,\"runtime_scale_bits\":%u,\"basis_column_bits\":",p->flags,p->kind,p->runtime_scale);
    words(f,&p->basis[0][0],9);fputs(",\"local_inertia_column_bits\":",f);words(f,&p->local_inertia[0][0],9);
    fputs(",\"translation_bits\":",f);words(f,p->translation,3);
    fputs(",\"local_center_bits\":",f);words(f,p->local_center,3);
    fputs(",\"directional\":[",f);
    for(unsigned i=0;i<p->directional_count;i++) {
        const SnowDirectionalInput *v=&p->directional[i];if(i)fputc(',',f);
        fprintf(f,"{\"enabled\":%u,\"point_bits\":",v->enabled);words(f,v->point,4);
        fputs(",\"direction_bits\":",f);words(f,v->direction,4);fputc('}',f);
    }
    fputs("],\"summed\":[",f);
    for(unsigned i=0;i<p->summed_count;i++) {
        const SnowSummedInput *v=&p->summed[i];if(i)fputc(',',f);
        fprintf(f,"{\"enabled\":%u,\"kind\":%u,\"point_bits\":",v->enabled,v->kind);words(f,v->point,4);
        fputs(",\"a_bits\":",f);words(f,v->a,4);fputs(",\"b_bits\":",f);words(f,v->b,4);fputc('}',f);
    }
    fputs("]}",f);
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
    fputs(",\"inverse_mass\":",f); floats(f,s->inverse_mass,2);
    fprintf(f,",\"point_attempted\":%u,\"point_valid\":%u,\"point_read_ticks\":%llu",s->point_attempted,s->point_valid,(unsigned long long)s->point_read_ticks);
    if(s->point_attempted) {
        const SnowPointDiagnostic *d=&s->point_diagnostic;
        fprintf(f,",\"point_diagnostic\":{\"stage\":%u,\"pass\":%u,\"reads\":%u,\"read_failed\":%u,\"count_valid\":%u,\"directional_count\":%llu,\"summed_count\":%llu}",d->stage,d->pass,d->reads,d->read_failed,d->count_valid,(unsigned long long)d->directional_count,(unsigned long long)d->summed_count);
    }
    if(s->point_valid) {fputs(",\"point_inputs\":",f);point_sample(f,&s->point_inputs);}
    fputc('}',f);
}
static void words(FILE *f,const uint32_t *v,unsigned n) {
    fputc('[',f);for(unsigned i=0;i<n;i++) { if(i) fputc(',',f);fprintf(f,"%u",v[i]); }fputc(']',f);
}
static void motion_sample(FILE *f,const SnowMotionObservation *m) {
    fputc('{',f);
#define U(name) fprintf(f,"\"" #name "\":%u,",m->name)
#define P(name) fprintf(f,"\"" #name "\":\"%llx\",",(unsigned long long)m->name)
    U(profile_valid);P(profile_handle);P(profile);U(smoothing_alpha_bits);
    P(motion);P(current);P(pending);P(state_current);P(state_pending);P(child_current);P(child_pending);
    U(current_mode);U(pending_mode);U(lock_word);U(lock_owner);U(lock_depth);U(query_depth);
    U(state_mode);U(state_pending_mode);U(child_mode);U(child_pending_mode);
    U(state_observed);U(child_observed);U(enabled);U(immediate);U(pending_service);
#undef U
#undef P
    fprintf(f,"\"latches\":[%u,%u,%u],\"ingested_bits\":",m->latches[0],m->latches[1],m->latches[2]);
    words(f,m->ingested,8);fputs(",\"current_input_bits\":",f);words(f,m->current_inputs,8);
    fputs(",\"nonzero_counts\":",f);words(f,m->nonzero_counts,2);
    fputs(",\"baseline_bits\":",f);words(f,m->baselines,12);fputc('}',f);
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
        size_t direct_substeps=0;
        if(drained) for(size_t i=0;i<used;i++) {
            SnowUpdateRecord r;
            if(!SnowProbe_ReadRecordSized(i,&r,sizeof r)) break;
            if(r.attribution_valid && r.frame_valid) ++direct_substeps;
        }
        LARGE_INTEGER frequency; QueryPerformanceFrequency(&frequency);
        fprintf(f,"{\"kind\":\"summary\",\"installed\":%d,\"restored\":%d,\"drained\":%d,\"records\":%llu,\"dropped\":%llu,\"qpf\":%llu,\"substep_available\":%s,\"direct_substep_records\":%llu,\"dispatch_counts_valid\":%d,\"selected_calls\":%llu,\"other_calls\":%llu}\n",
          installed,restored,drained,(unsigned long long)used,(unsigned long long)dropped,(unsigned long long)frequency.QuadPart,direct_substeps ? "true" : "false",(unsigned long long)direct_substeps,counts_valid,(unsigned long long)counts.selected_calls,(unsigned long long)counts.other_calls);
        if(drained) for(size_t i=0;i<used;i++) {
            SnowUpdateRecord r; if(!SnowProbe_ReadRecordSized(i,&r,sizeof r)) break;
            fprintf(f,"{\"kind\":\"record\",\"index\":%llu,\"actor\":\"%llx\",\"thread\":%llu,\"entry\":%llu,\"exit\":%llu,\"elapsed\":",
              (unsigned long long)i,(unsigned long long)r.actor,(unsigned long long)r.thread,
              (unsigned long long)r.entry_tick,(unsigned long long)r.exit_tick);
            number(f,r.elapsed); fputs(",\"derivative\":",f); number(f,r.derivative);
            fprintf(f,",\"attribution_attempted\":%u,\"attribution_valid\":%u",
                    r.attribution_attempted,r.attribution_valid);
            if(r.attribution_valid) fprintf(f,",\"job\":\"%llx\",\"record_index\":%u,\"initial_count\":%u",
                    (unsigned long long)r.attribution.job,r.attribution.record_index,r.attribution.initial_count);
            fprintf(f,",\"frame_valid\":%u",r.frame_valid);
            if(r.frame_valid) fprintf(f,",\"substep_ordinal\":%u,\"selected_count\":%u,\"outer_completion_counter\":%llu",
                r.frame.ordinal,r.frame.selected_count,(unsigned long long)r.frame.outer_completion_counter);
            fprintf(f,",\"motion_attempted\":%u,\"motion_before_valid\":%u,\"motion_after_valid\":%u",
                    r.motion_attempted,r.motion_before_valid,r.motion_after_valid);
            if(r.motion_before_valid) { fputs(",\"motion_before\":",f);motion_sample(f,&r.motion_before); }
            if(r.motion_after_valid) { fputs(",\"motion_after\":",f);motion_sample(f,&r.motion_after); }
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
    /* Build-specific route; binding acquisition already verifies the adapter build.
     * Additional function-table joins are checked before opting into attribution. */
    SnowEntryProfile profile={0x1413adbacull,0x142916ee0ull,0x142917108ull,binding.actor_table,0x141389ad8ull};
    uint64_t visitor=0,dispatcher=0; SIZE_T got=0;
    if(attribute_jobs &&
       (!ReadProcessMemory(GetCurrentProcess(),(void *)(uintptr_t)(profile.job_table+0x80),&visitor,8,&got) || got!=8 || visitor!=0x1413adb70ull ||
        !ReadProcessMemory(GetCurrentProcess(),(void *)(uintptr_t)(profile.callable_table+0x10),&dispatcher,8,&got) || got!=8 || dispatcher!=0x1413cd590ull)) {
        host->log(host->context,"entry attribution route mismatch"); InterlockedExchange(&phase,3); return 0;
    }
    uint64_t image_base=0,image_size=0;
    if(observe_points) {
        HMODULE image=GetModuleHandleA(NULL);
        IMAGE_DOS_HEADER dos;IMAGE_NT_HEADERS64 nt;
        if(!image || !ReadProcessMemory(GetCurrentProcess(),image,&dos,sizeof dos,&got) || got!=sizeof dos ||
           dos.e_magic!=IMAGE_DOS_SIGNATURE || dos.e_lfanew<0 || dos.e_lfanew>0x100000 ||
           !ReadProcessMemory(GetCurrentProcess(),(const char *)image+dos.e_lfanew,&nt,sizeof nt,&got) || got!=sizeof nt ||
           nt.Signature!=IMAGE_NT_SIGNATURE || nt.OptionalHeader.Magic!=IMAGE_NT_OPTIONAL_HDR64_MAGIC) {
            host->log(host->context,"point profile image header rejected");InterlockedExchange(&phase,3);return 0;
        }
        image_base=(uint64_t)(uintptr_t)image;image_size=nt.OptionalHeader.SizeOfImage;
    }
    int configured=SnowProbe_ConfigureDetailed(&binding,original,attribute_jobs ? &profile : NULL,observe_motion,image_base,image_size);
    if(!configured) {
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
    attribute_jobs=GetPrivateProfileIntA("capture","attribute_jobs",0,api->config_path)==1;
    observe_motion=GetPrivateProfileIntA("capture","observe_motion",0,api->config_path)==1;
    observe_points=GetPrivateProfileIntA("capture","observe_points",0,api->config_path)==1;
    host=api; milliseconds=seconds*1000;
    plugin->struct_size=sizeof *plugin; plugin->api_version=SNOW_PLUGIN_API_VERSION;
    plugin->name="update_capture"; plugin->version="experimental-9";
    plugin->on_pause=paused; plugin->on_resume=resumed;
    return 0;
}
