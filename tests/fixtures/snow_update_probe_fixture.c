#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "snow_update_probe.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned char actor[0x1200],entity[0x100],runtime[0x1600],main_body[0x300],rider[0x300],world[8],table[8];
static uint32_t request=7,substep=2,calls;
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
int main(int argc,char **argv) {
    assert(argc==2); HMODULE dll=LoadLibraryA(argv[1]); assert(dll);
    int (*configure)(const SnowUpdateBinding *,SnowUpdateOriginal)=(void *)GetProcAddress(dll,"SnowProbe_Configure");
    void (*dispatch)(void *,float,float)=(void *)GetProcAddress(dll,"SnowProbe_Dispatch");
    int (*close_probe)(size_t *,size_t *)=(void *)GetProcAddress(dll,"SnowProbe_Close");
    int (*get)(size_t,SnowUpdateRecord *)=(void *)GetProcAddress(dll,"SnowProbe_ReadRecord");
    assert(configure && dispatch && close_probe && get);
    q(actor,table); q(actor+0x1050,actor); q(actor+0x10,entity); q(entity+0x60,world);
    q(actor+0x168,runtime); q(runtime+0x6e8,main_body); q(runtime+0xb90,rider);
    f(main_body+0x1a0,10); f(main_body+0x1ac,3); f(rider+0x1ac,9);
    SnowUpdateBinding b={(uintptr_t)actor,(uintptr_t)table,(uintptr_t)world,(uintptr_t)&request,(uintptr_t)&substep};
    SnowUpdateRecord r; size_t used=0,dropped=0;
    assert(configure(&b,original)); assert(!configure(&b,original)); assert(!get(0,&r));
    dispatch(actor,.125f,.5f); dispatch(&other,.125f,.5f);
    change_identity=1; dispatch(actor,.125f,.5f); change_identity=0; q(actor+0x168,runtime);
    assert(close_probe(&used,&dropped)); assert(used==2 && dropped==0 && calls==3);
    assert(get(1,&r) && r.before.valid==3 && r.after.valid==0);
    assert(get(0,&r) && !get(2,&r));
    assert(r.before.valid==3 && r.after.valid==3 && r.thread!=0);
    assert(r.before.linear[0][0]==10 && r.after.linear[0][0]==12);
    assert(r.before.angular[0][0]==3 && r.after.angular[0][0]==3);
    assert(r.before.angular[1][0]==9 && r.after.angular[1][0]==9);
    assert(r.elapsed==.125f && r.derivative==.5f && r.after.request==7 && r.after.substep==2);
    SnowUpdateRecord saved=r; dispatch(actor,.125f,.5f); assert(calls==4);
    assert(get(0,&r) && memcmp(&r,&saved,sizeof r)==0);
    assert(FreeLibrary(dll)); /* pinned code must remain callable */
    dispatch(actor,.125f,.5f); assert(calls==5);
    puts("PASS: Windows DLL capture, filtered forwarding, closed reads, late calls and pinning");
    return 0;
}
