#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "snow_update_probe.h"
#include "snow_plugin.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned char actor[0x1200],entity[0x100],runtime[0x1600],main_body[0x300],rider[0x300],world[8];
static __attribute__((section(".tracevt"),aligned(4096))) unsigned char table[4096]={1};
static uint32_t request=7,calls;
static int other, change_identity;
static void q(void *dst,void *p) { uint64_t v=(uintptr_t)p; memcpy(dst,&v,8); }
static void f(void *dst,float v) { memcpy(dst,&v,4); }
static void original(void *self,float elapsed,float derivative) {
    assert(self==actor || self==&other); assert(elapsed==.125f && derivative==.5f); calls++;
    if(self!=actor) return;
    /* Authored synthetic effect; not an invocation of recovered game code. */
    float v; memcpy(&v,main_body+0x1a0,4); f(main_body+0x1a0,v+2);
    if(change_identity) q(actor+0x168,NULL);
}
static void log_line(void *ctx,const char *line) { (void)ctx; puts(line); }
int main(int argc,char **argv) {
    assert(argc==3);
    HMODULE dll=LoadLibraryA(argv[1]); assert(dll);
    SnowModInitializeFn initialize=(void *)GetProcAddress(dll,"SnowMod_Initialize");
    void (*set_binding)(const SnowUpdateBinding *,SnowUpdateOriginal)=(void *)GetProcAddress(dll,"FixtureBinding");
    assert(initialize && set_binding);
    q(actor,table); q(actor+0x1050,actor); q(actor+0x10,entity); q(entity+0x60,world);
    q(actor+0x168,runtime); q(runtime+0x6e8,main_body); q(runtime+0xb90,rider);
    q(table+0x2c0,(void *)original);
    f(main_body+0x1a0,10); f(main_body+0x1ac,3); f(rider+0x1ac,9);
    SnowUpdateBinding b={(uintptr_t)actor,(uintptr_t)table,(uintptr_t)world,(uintptr_t)&request,0};
    set_binding(&b,original);
    SnowHostApiV1 api={0}; api.struct_size=sizeof api; api.api_version=SNOW_PLUGIN_API_VERSION;
    api.log=log_line; api.config_path=argv[2];
    SnowPluginV1 plugin={0};
    DeleteFileA(argv[2]); assert(initialize(&api,&plugin)!=0);
    FILE *fout=fopen(argv[2],"w"); assert(fout); fputs("[capture]\nenabled=1\nseconds=1\n",fout); fclose(fout);
    assert(initialize(&api,&plugin)==0);
    assert(plugin.on_pause(NULL)==0); assert(plugin.on_resume(NULL,SNOW_RESUME_REQUESTED)==0);
    for(unsigned i=0;i<700;i++) {
        SnowUpdateOriginal fn=(void *)InterlockedCompareExchangePointer((void *volatile *)(table+0x2c0),NULL,NULL);
        fn(actor,.125f,.5f); Sleep(2);
    }
    char output[MAX_PATH]; snprintf(output,sizeof output,"%s.trace.jsonl",argv[2]);
    ULONGLONG deadline=GetTickCount64()+3000;
    while(GetFileAttributesA(output)==INVALID_FILE_ATTRIBUTES && GetTickCount64()<deadline) Sleep(10);
    assert(GetFileAttributesA(output)!=INVALID_FILE_ATTRIBUTES);
    assert((void *)InterlockedCompareExchangePointer((void *volatile *)(table+0x2c0),NULL,NULL)==(void *)original);
    assert(calls==700);
    puts("PASS: opt-in plugin configured on pause, captured on resume, restored and exported");
    return 0;
}
