#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "snow_update_probe.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static __attribute__((aligned(16))) unsigned char actor[0x1800],entity[0x100],runtime[0x1600],main_body[0x300],rider[0x300],world[0x1000],physics_manager[64];
static __attribute__((section(".tracevt"),aligned(4096))) unsigned char table[4096]={1};
static uint32_t request=7,substep=2,calls;
static unsigned char job[0x1c00],timing[0x1400],callable[16],records[80],job_table[16],callable_table[16];
static uint64_t range_base;
static unsigned char profile_handle[16],motion_profile[0x100];
extern void fixture_entry_call(void *,float,float,const SnowEntryRegisters *,SnowUpdateOriginal);
extern unsigned char fixture_entry_return[];
static int other, change_identity, motion_case;
static void q(void *dst,void *p) { uint64_t v=(uintptr_t)p; memcpy(dst,&v,8); }
static void f(void *dst,float v) { memcpy(dst,&v,4); }
static void original(void *self,float elapsed,float derivative) {
    assert(self==actor || self==&other); assert(elapsed==.125f && derivative==.5f); calls++;
    if(self!=actor) return;
    /* Authored synthetic effect; not an invocation of recovered game code. */
    uint32_t counter; memcpy(&counter,runtime+0xa80,4); counter--; memcpy(runtime+0xa80,&counter,4);
    float v; memcpy(&v,main_body+0x1a0,4); f(main_body+0x1a0,v+2);
    if(change_identity) { q(actor+0x168,NULL); if(motion_case) q(actor+0x1050,NULL); }
}
static void competitor(void *a,float b,float c) { (void)a; (void)b; (void)c; }
static void set_slot(void *value) {
    DWORD old,ignored; assert(VirtualProtect(table,sizeof table,PAGE_READWRITE,&old));
    q(table+0x2c0,value); assert(VirtualProtect(table,sizeof table,old,&ignored));
}
static SnowUpdateOriginal read_slot(void) {
    SnowUpdateOriginal fn; memcpy(&fn,table+0x2c0,sizeof fn); return fn;
}
static void readonly_table(void) {
    MEMORY_BASIC_INFORMATION info; assert(VirtualQuery(table,&info,sizeof info));
    assert(info.Protect==PAGE_READONLY);
}
int main(int argc,char **argv) {
    assert(argc==2 || argc==3); HMODULE dll=LoadLibraryA(argv[1]); assert(dll);
    motion_case=argc==3 && !strcmp(argv[2],"motion");
    int bad_frame=argc==3 && !strcmp(argv[2],"invalid-frame");
    int valid_attribution=motion_case || bad_frame || (argc==3 && !strcmp(argv[2],"valid-attribution"));
    int attributed=valid_attribution || (argc==3 && !strcmp(argv[2],"attributed"));
    int conflict=argc==3 && !attributed;
    int (*configure_observed)(const SnowUpdateBinding *,SnowUpdateOriginal,const SnowEntryProfile *,int)=(void *)GetProcAddress(dll,"SnowProbe_ConfigureObserved");
    assert(configure_observed);
    int (*configure_attributed)(const SnowUpdateBinding *,SnowUpdateOriginal,const SnowEntryProfile *)=(void *)GetProcAddress(dll,"SnowProbe_ConfigureAttributed");
    int (*configure)(const SnowUpdateBinding *,SnowUpdateOriginal)=(void *)GetProcAddress(dll,"SnowProbe_Configure");
    void (*dispatch)(void *,float,float)=(void *)GetProcAddress(dll,"SnowProbe_Dispatch");
    int (*close_probe)(size_t *,size_t *)=(void *)GetProcAddress(dll,"SnowProbe_Close");
    int (*get)(size_t,void *,size_t)=(void *)GetProcAddress(dll,"SnowProbe_ReadRecordSized");
    uint32_t (*abi)(void)=(void *)GetProcAddress(dll,"SnowProbe_ABIVersion");
    size_t (*record_size)(void)=(void *)GetProcAddress(dll,"SnowProbe_RecordSize");
    assert(abi && record_size && abi()==SNOW_PROBE_ABI_VERSION && record_size()==sizeof(SnowUpdateRecord));
    int (*install)(void)=(void *)GetProcAddress(dll,"SnowProbe_InstallSlot");
    int (*restore)(void)=(void *)GetProcAddress(dll,"SnowProbe_RestoreSlot");
    int (*counts)(SnowProbeDispatchCounts *)=(void *)GetProcAddress(dll,"SnowProbe_ReadDispatchCounts");
    SnowProbeDispatchCounts c={99,99};
    assert(counts && !counts(&c) && c.selected_calls==0 && c.other_calls==0);
    assert(configure && dispatch && close_probe && get && install && restore);
    q(table+0x2c0,conflict ? (void *)competitor : (void *)original);
    DWORD old; assert(VirtualProtect(table,sizeof table,PAGE_READONLY,&old));
    if(motion_case) {
        q(actor+0x1060,profile_handle);q(profile_handle,motion_profile);
        uint32_t signed_status=0x80000000u;memcpy(profile_handle+12,&signed_status,4);
        f(motion_profile+0x64,.1f);
    }
    q(actor,table); q(actor+0x1050,actor); q(actor+0x10,entity); q(entity+0x60,world);
    q(actor+0x168,runtime); q(runtime+0x6e8,main_body); q(runtime+0xb90,rider);
    f(main_body+0x1a0,10); f(main_body+0x1ac,3); f(rider+0x1ac,9);
    SnowUpdateBinding b={(uintptr_t)actor,(uintptr_t)table,(uintptr_t)world,(uintptr_t)&request,(uintptr_t)&substep};
    SnowUpdateRecord r; size_t used=0,dropped=0;
    SnowEntryProfile profile={1,2,3,(uintptr_t)table,0}; /* intentionally wrong route */
    SnowEntryRegisters entry={(uintptr_t)job,(uintptr_t)&range_base,1,0,0};
    if(valid_attribution) {
        profile.return_address=(uintptr_t)fixture_entry_return;
        profile.batch_return=0x9876;
        q(job+0x1b58,(void *)(uintptr_t)profile.batch_return);
        q(job+0x1b60,timing);q(job+0x1b70,(void *)(uintptr_t)1);
        q(timing,physics_manager);q(world+0xff0,physics_manager);q(physics_manager+0x18,timing);uint32_t steps=2;memcpy(timing+0x1390,&steps,4);
        f(timing+0x1394,.125f);f(timing+0x136c,bad_frame ? .25f : .5f);q(physics_manager+0x20,(void *)(uintptr_t)42);
        profile.job_table=(uintptr_t)job_table;profile.callable_table=(uintptr_t)callable_table;
        q(job,job_table);q(job+0x198,records);q(job+0x1f8,callable);
        uint32_t count=5;memcpy(job+0x1a4,&count,4);q(callable,callable_table);
        range_base=(uintptr_t)(records+32);q(records+56,actor);
    }
    assert(motion_case ? configure_observed(&b,original,&profile,1) : (attributed ? configure_attributed(&b,original,&profile) : configure(&b,original))); assert(!configure(&b,original)); assert(!get(0,&r,sizeof r));
    assert(counts(&c) && c.selected_calls==0 && c.other_calls==0);
    assert(!counts(NULL));
    if(conflict) {
        assert(!install()); assert(read_slot()==competitor); assert(restore()); readonly_table();
        puts("PASS: mismatched original refused without slot mutation"); return 0;
    }
    assert(install()==1); assert(!install()); readonly_table();
    SnowUpdateOriginal installed_target=read_slot();
    assert(attributed ? installed_target!=dispatch : installed_target==dispatch);
    if(valid_attribution) fixture_entry_call(actor,.125f,.5f,&entry,read_slot());
    else read_slot()(actor,.125f,.5f);
    read_slot()(&other,.125f,.5f);
    change_identity=1; dispatch(actor,.125f,.5f); change_identity=0; q(actor+0x168,runtime);
    set_slot((void *)competitor); assert(restore()==0); assert(read_slot()==competitor); readonly_table();
    set_slot((void *)installed_target); assert(restore()==1); assert(read_slot()==original); readonly_table();
    assert(restore()==1);
    assert(counts(&c) && c.selected_calls==2 && c.other_calls==1);
    assert(close_probe(&used,&dropped)); assert(used==2 && dropped==0 && calls==3);
    assert(get(1,&r,sizeof r) && r.before.valid==15 && r.after.valid==0);
    if(motion_case) {
        SnowMotionObservation blank={0};
        assert(r.motion_attempted && r.motion_before_valid && !r.motion_after_valid);
        assert(!memcmp(&r.motion_after,&blank,sizeof blank));
    }
    assert(get(0,&r,sizeof r) && !get(2,&r,sizeof r));
    assert(r.motion_attempted==(unsigned)motion_case);
    if(motion_case) {
        assert(r.motion_before_valid && r.motion_after_valid);
        assert(r.motion_before.profile_valid && r.motion_after.profile_valid);
        assert(r.motion_before.smoothing_alpha_bits==0x3dcccccdu);
        assert(r.motion_before.motion==(uintptr_t)(actor+0x1010));
    }
    assert(r.attribution_attempted==(unsigned)attributed && r.attribution_valid==(unsigned)valid_attribution);
    if(valid_attribution) {
        assert(r.frame_valid==(unsigned)!bad_frame);
        if(!bad_frame) assert(r.frame.ordinal==1 && r.frame.selected_count==2 && r.frame.outer_completion_counter==42);
        else { SnowBatchFrame zero={0}; assert(!memcmp(&r.frame,&zero,sizeof zero)); }
        assert(r.attribution.job==(uintptr_t)job && r.attribution.record==(uintptr_t)(records+48));
        assert(r.attribution.actor==(uintptr_t)actor && r.attribution.record_index==3 && r.attribution.initial_count==5);
    }
    assert(r.before.valid==15 && r.after.valid==15 && r.thread!=0);
    assert(r.before.preconsume_counter==0 && r.after.preconsume_counter==-1);
    assert(r.before.linear[0][0]==10 && r.after.linear[0][0]==12);
    assert(r.before.angular[0][0]==3 && r.after.angular[0][0]==3);
    assert(r.before.angular[1][0]==9 && r.after.angular[1][0]==9);
    assert(r.elapsed==.125f && r.derivative==.5f && r.after.request==7 && r.after.substep==2);
    SnowUpdateRecord saved=r; dispatch(actor,.125f,.5f); assert(calls==4);
    assert(get(0,&r,sizeof r) && memcmp(&r,&saved,sizeof r)==0);
    assert(FreeLibrary(dll)); /* pinned code must remain callable */
    dispatch(actor,.125f,.5f); assert(calls==5);
    assert(counts(&c) && c.selected_calls==4 && c.other_calls==1);
    puts("PASS: Windows DLL capture, filtered forwarding, closed reads, late calls, pinning, slot installation, protection restoration and conflict refusal");
    return 0;
}
