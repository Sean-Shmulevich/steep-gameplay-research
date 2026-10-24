/* Opt-in one-shot markup update capture. Controller supplies fresh addresses only after
 * acquisition, then creates the trigger. Raw per-session provenance is private.
 * No code patching or game calls; one image data slot is temporarily replaced.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "snow_plugin.h"
#include "snow_markup_update_probe.h"
static char config[MAX_PATH],trigger[MAX_PATH+16],output[MAX_PATH+16],done[MAX_PATH+16],armed[MAX_PATH+16];
static volatile LONG cancelled;
static unsigned duration;
static struct {uint64_t base,size,component,owner,actor,world;} binding;
static int read_mem(void *ctx,uint64_t at,void *out,size_t n) {
    (void)ctx;SIZE_T got=0;
    return ReadProcessMemory(GetCurrentProcess(),(void *)(uintptr_t)at,out,n,&got) && got==n;
}
static int signature(uint32_t rva,size_t n,uint64_t expected) {
    unsigned char bytes[160];uint64_t h=UINT64_C(14695981039346656037);
    if(n>sizeof bytes || !read_mem(NULL,binding.base+rva,bytes,n))return 0;
    for(size_t i=0;i<n;i++)h=(h^bytes[i])*UINT64_C(1099511628211);
    return h==expected;
}
static int pointer_config(const char *key,uint64_t *out) {
    char text[40],*end=NULL;GetPrivateProfileStringA("capture",key,"",text,sizeof text,config);
    if(!text[0] || text[0]=='-')return 0;
    *out=strtoull(text,&end,16);
    return end && !*end && *out>=0x10000 && *out<UINT64_C(0x800000000000);
}
static int owner_matches(void) {
    uint64_t owner=0,world=0,actor_table=0,self=0;
    return read_mem(NULL,binding.actor,&actor_table,8) && actor_table==binding.base+0x1e7a350 &&
        read_mem(NULL,binding.actor+0x1050,&self,8) && self==binding.actor &&
        read_mem(NULL,binding.actor+0x10,&owner,8) && owner==binding.owner &&
        read_mem(NULL,binding.owner+0x60,&world,8) && world==binding.world;
}
static int observe(void *ctx,void *component,SnowMarkupUpdateSnapshot *s) {
    (void)ctx;
    return (uintptr_t)component==binding.component && owner_matches() &&
        snow_markup_provider_observe(read_mem,NULL,binding.component,binding.base,binding.size,s) && owner_matches();
}
static void write_snapshot(FILE *f,const SnowMarkupUpdateSnapshot *s,unsigned valid) {
    fprintf(f,"{\"valid\":%u,\"count\":%u,\"notification_count\":%u,\"attachment_present\":%u,\"rows\":[",valid,s->record_count,s->notification_count,(unsigned)(s->attachment!=0));
    for(unsigned i=0;valid && i<s->record_count && i<SNOW_MARKUP_RECORD_LIMIT;i++) {
        const SnowMarkupScalarRecord *r=&s->records[i];
        fprintf(f,"%s{\"key\":%u,\"scalar54_bits\":%u,\"start_bits\":%u,\"end_bits\":%u,\"flags\":%u}",i?",":"",r->key,r->scalar54_bits,r->start_bits,r->end_bits,(unsigned)r->flags);
    }
    fputs("]}",f);
}
static DWORD WINAPI capture(LPVOID unused) {
    (void)unused;ULONGLONG until=GetTickCount64()+180000;
    while(GetFileAttributesA(trigger)==INVALID_FILE_ATTRIBUTES) {
        if(InterlockedCompareExchange(&cancelled,0,0) || GetTickCount64()>=until)return 0;
        Sleep(10);
    }
    if(InterlockedCompareExchange(&cancelled,0,0))return 0;
    binding.base=(uintptr_t)GetModuleHandleW(NULL);
    int compatible=pointer_config("size",&binding.size) && pointer_config("component",&binding.component) &&
        pointer_config("owner",&binding.owner) && pointer_config("actor",&binding.actor) && pointer_config("world",&binding.world) &&
        signature(0x53c760,71,UINT64_C(0xb7be082992817535)) && signature(0x34df20,79,UINT64_C(0x863f76cdb22593ad)) && signature(0x5eab70,9,UINT64_C(0xe39a6dd66384e0d3));
    SnowMarkupUpdateSnapshot initial;
    int guarded=compatible && observe(NULL,(void *)(uintptr_t)binding.component,&initial);
    int configured=0,installed=0,restored=0,drained=0;size_t used=0,dropped=0;
    if(guarded)configured=SnowMarkupUpdateProbe_Configure(binding.base+0x1e789b8+0x4b0,
        (SnowMarkupUpdateOriginal)(uintptr_t)(binding.base+0x53c760),(void *)(uintptr_t)binding.component,observe,NULL);
    if(configured) {
        installed=SnowMarkupUpdateProbe_InstallSlot();
        if(installed==1) {
            FILE *marker=fopen(armed,"w");
            if(marker){fputs("dispatch slot installed\n",marker);fclose(marker);}
            until=GetTickCount64()+duration;
            while(GetTickCount64()<until && !InterlockedCompareExchange(&cancelled,0,0))Sleep(1);
        }
        restored=SnowMarkupUpdateProbe_RestoreSlot();
        until=GetTickCount64()+2000;
        while(restored!=1 && GetTickCount64()<until) {Sleep(10);restored=SnowMarkupUpdateProbe_RestoreSlot();}
        until=GetTickCount64()+2000;
        do {drained=SnowMarkupUpdateProbe_Close(&used,&dropped);if(drained)break;Sleep(1);}while(GetTickCount64()<until);
    }
    uint64_t slot=0;int slot_original=read_mem(NULL,binding.base+0x1e789b8+0x4b0,&slot,8) && slot==binding.base+0x53c760;
    FILE *f=fopen(output,"w");
    if(f) {
        fprintf(f,"{\"kind\":\"summary\",\"compatible\":%d,\"guarded\":%d,\"configured\":%d,\"installed\":%d,\"restored\":%d,\"drained\":%d,\"slot_original\":%d,\"used\":%llu,\"dropped\":%llu,\"frequency\":%llu}\n",
            compatible,guarded,configured,installed,restored,drained,slot_original,(unsigned long long)used,(unsigned long long)dropped,(unsigned long long)SnowMarkupUpdateProbe_ClockFrequency());
        if(drained)for(size_t i=0;i<used;i++) {
            SnowMarkupUpdateRecord r;if(!SnowMarkupUpdateProbe_ReadRecordSized(i,&r,sizeof r))break;
            fprintf(f,"{\"kind\":\"record\",\"index\":%llu,\"entry\":%llu,\"exit\":%llu,\"thread\":%llu,\"caller\":\"%llx\",\"argument_bits\":%u,\"before\":",(unsigned long long)i,(unsigned long long)r.entry_tick,(unsigned long long)r.exit_tick,(unsigned long long)r.thread,(unsigned long long)r.caller,r.argument_bits);
            write_snapshot(f,&r.before,r.before_valid);fputs(",\"after\":",f);write_snapshot(f,&r.after,r.after_valid);fputs("}\n",f);
        }
        fclose(f);
        f=fopen(done,"w");if(f){fputs("capture complete\n",f);fclose(f);}
    }
    return 0;
}
static void unload(void *unused) {(void)unused;InterlockedExchange(&cancelled,1);}
__declspec(dllexport) int SnowMod_Initialize(const SnowHostApiV1 *api,SnowPluginV1 *plugin) {
    HMODULE pinned;
    if(!api || !plugin || api->api_version!=SNOW_PLUGIN_API_VERSION || api->struct_size<sizeof *api || !api->config_path ||
       strlen(api->config_path)+16>=MAX_PATH || GetPrivateProfileIntA("capture","enabled",0,api->config_path)!=1)return 1;
    strcpy(config,api->config_path);duration=GetPrivateProfileIntA("capture","milliseconds",500,config);
    if(duration<100 || duration>1000)return 1;
    snprintf(trigger,sizeof trigger,"%s.trigger",config);snprintf(output,sizeof output,"%s.trace.jsonl",config);snprintf(done,sizeof done,"%s.done",config);snprintf(armed,sizeof armed,"%s.armed",config);
    if(GetFileAttributesA(trigger)!=INVALID_FILE_ATTRIBUTES || GetFileAttributesA(done)!=INVALID_FILE_ATTRIBUTES || GetFileAttributesA(armed)!=INVALID_FILE_ATTRIBUTES)return 1;
    if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)(uintptr_t)&capture,&pinned))return 1;
    plugin->struct_size=sizeof *plugin;plugin->api_version=SNOW_PLUGIN_API_VERSION;plugin->name="markup_update_capture";plugin->version="experimental-1";plugin->on_unload=unload;
    HANDLE worker=CreateThread(NULL,0,capture,NULL,0,NULL);if(!worker)return 1;CloseHandle(worker);return 0;
}
