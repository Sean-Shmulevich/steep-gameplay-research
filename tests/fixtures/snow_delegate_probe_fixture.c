#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "snow_delegate_probe.h"
static void *owner_global,*expected_receiver;
static uintptr_t table[16],physics_actor_table[100],physics_runtime_table[1];
static unsigned char *physics_memory;
static unsigned physics_mode;
static void putq(size_t offset,uintptr_t value){memcpy(physics_memory+offset,&value,8);}
static void putf(size_t offset,float value){memcpy(physics_memory+offset,&value,4);}
static volatile LONG calls;
static HANDLE entered_event,release_event;
static SnowDelegateOriginal worker_callback;
static void *worker_storage,*worker_receiver;
static DWORD WINAPI invoke_worker(LPVOID unused){(void)unused;
    assert(worker_callback(worker_storage,worker_receiver)==UINT64_C(0xfedcba9876543210));return 0;}
static int invalidate,mutate_descriptor;
static unsigned job_offset=0x218;
static uintptr_t body(void *receiver) { assert(receiver==expected_receiver);InterlockedIncrement(&calls);
    InterlockedIncrement((LONG *)((unsigned char *)receiver+job_offset+0x4c+16));
    if(entered_event){SetEvent(entered_event);assert(WaitForSingleObject(release_event,5000)==WAIT_OBJECT_0);}
    if(physics_memory) {
        putf(0x51a0,2.0f);
        if(physics_mode==2)putq(0x2060,(uintptr_t)physics_memory+0xb000);
        if(physics_mode==3)putq(0x36e8,(uintptr_t)physics_memory+0x7000);
        if(physics_mode==5)putq(0x3000,0);
        if(physics_mode==6){putf(0x1170,0.75f);putq(0xd018,1);}
        if(physics_mode==7)putq(0x1050,0);
        if(physics_mode==8)putq(0x1020,0);
        if(physics_mode==9)putq(0xc020,1);
    }
    if(mutate_descriptor)((uintptr_t *)((unsigned char *)receiver+job_offset+0x198))[1]^=1;
    if(invalidate)owner_global=NULL;
    return UINT64_C(0xfedcba9876543210); }
static uintptr_t invoker(void *storage,void *receiver) { return (*(uintptr_t (**)(void *))storage)(receiver); }
static uintptr_t competitor(void *storage,void *receiver) { (void)storage;(void)receiver;return 5; }
static void dispatch_method(void) {}
int main(int argc,char **argv) {
    assert(argc==3 || argc==4);
    int engine=argc==4 && !strcmp(argv[3],"engine");
    if(engine)job_offset=0x740;
    HMODULE dll=LoadLibraryA(argv[1]);assert(dll);
    int (*configure)(const SnowDelegateBinding *)=(void *)GetProcAddress(dll,"SnowDelegateProbe_Configure");
    int (*configure_site)(const SnowDelegateBinding *,SnowDelegateSite)=(void *)GetProcAddress(dll,"SnowDelegateProbe_ConfigureSite");
    int (*install)(void)=(void *)GetProcAddress(dll,"SnowDelegateProbe_Install");
    int (*restore)(void)=(void *)GetProcAddress(dll,"SnowDelegateProbe_Restore");
    int (*close_probe)(size_t *,size_t *)=(void *)GetProcAddress(dll,"SnowDelegateProbe_Close");
    int (*read_record)(size_t,void *,size_t)=(void *)GetProcAddress(dll,"SnowDelegateProbe_Read");
    size_t (*record_size)(void)=(void *)GetProcAddress(dll,"SnowDelegateProbe_RecordSize");
    uint32_t (*abi)(void)=(void *)GetProcAddress(dll,"SnowDelegateProbe_ABIVersion");
    assert(configure&&configure_site&&install&&restore&&close_probe&&read_record&&record_size&&abi);
    int (*arm)(uint64_t)=(void *)GetProcAddress(dll,"SnowDelegateProbe_ArmObservation");
    int (*read_request)(SnowDelegateRequestObservation *)=(void *)GetProcAddress(dll,"SnowDelegateProbe_ReadObservation");
    SnowObservationAdmission (*submit)(uint64_t)=(void *)GetProcAddress(dll,"SnowDelegateProbe_SubmitObservation");
    SnowObservationReceipt (*collect)(SnowDelegateRequestObservation *)=(void *)GetProcAddress(dll,"SnowDelegateProbe_CollectObservation");
    void (*close_requests)(void)=(void *)GetProcAddress(dll,"SnowDelegateProbe_CloseObservations");
    int (*configure_physics)(uint64_t,const SnowUpdateProfile *)=(void *)GetProcAddress(dll,"SnowDelegateProbe_ConfigurePhysics");
    SnowObservationReceipt (*collect_physics)(SnowDelegateRequestObservation *,SnowDelegatePhysicsObservation *)=(void *)GetProcAddress(dll,"SnowDelegateProbe_CollectPhysics");
    int (*enable_motion)(void)=(void *)GetProcAddress(dll,"SnowDelegateProbe_EnableMotion");
    SnowObservationReceipt (*collect_state)(SnowDelegateRequestObservation *,SnowDelegatePhysicsObservation *,SnowDelegateMotionObservation *)=(void *)GetProcAddress(dll,"SnowDelegateProbe_CollectState");
    assert(configure_physics&&collect_physics&&enable_motion&&collect_state);
    assert(!enable_motion());
    assert(arm&&read_request&&submit&&collect&&close_requests);SnowDelegateRequestObservation request={0};
    assert(submit(1)==SNOW_OBSERVATION_INVALID);assert(!collect(&request));
    assert(!arm(9));assert(!read_request(&request));
    assert(abi()==3 && record_size()==sizeof(SnowDelegateRecord));
    owner_global=VirtualAlloc(NULL,0x1000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(owner_global);
    expected_receiver=owner_global;
    unsigned char *owner=owner_global;table[0x40/8]=(uintptr_t)&dispatch_method;
    *(uintptr_t *)(owner+job_offset)=(uintptr_t)table;
    uintptr_t *d=(uintptr_t *)(owner+job_offset+0x198);
    d[0]=(uintptr_t)&body;d[1]=0;d[2]=(uintptr_t)owner|2;d[3]=(uintptr_t)&invoker;
    SnowDelegateBinding b={(uintptr_t)&owner_global,(uintptr_t)owner,(uintptr_t)table,
        (uintptr_t)&dispatch_method,d[0],d[1],d[2],d[3]};
    assert(!configure_site(&b,(SnowDelegateSite)99));
    assert(engine?configure_site(&b,SNOW_DELEGATE_ENGINE_MAIN):configure(&b));
    assert(!configure(&b));
    if(!strncmp(argv[2],"physics",7)) {
        assert(engine);
        physics_mode=!strcmp(argv[2],"physics_world")?2:!strcmp(argv[2],"physics_body")?3:
            !strcmp(argv[2],"physics_no_rider")?4:!strcmp(argv[2],"physics_profile")?5:!strcmp(argv[2],"physics_motion")?6:
            !strcmp(argv[2],"physics_motion_bad")?7:!strcmp(argv[2],"physics_motion_missing")?8:!strcmp(argv[2],"physics_motion_only_bad")?9:1;
        physics_memory=VirtualAlloc(NULL,0x10000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(physics_memory);
        uintptr_t a=(uintptr_t)physics_memory;
        SnowUpdateProfile profile={(uintptr_t)physics_actor_table,(uintptr_t)physics_runtime_table,
            (uintptr_t)&body,(uintptr_t)&invoker};
        physics_actor_table[0x2c0/8]=(uintptr_t)&body;
        putq(0,profile.actor_table);putq(0x1050,a);putq(0x10,a+0x2000);putq(0x2060,a+0x8000);
        putq(0x168,a+0x3000);putq(0x3000,profile.runtime_table);putq(0x36f0,a);
        putq(0x36e8,a+0x5000);putq(0x3b90,physics_mode==4?0:a+0x6000);
        putq(0x8ff0,a+0x9000);putq(0x9018,a+0xa000);putq(0xa000,a+0x9000);
        putq(0xa010,a+0xa1b0);putq(0xa360,profile.world_step_callback);putq(0xa208,19);
        putf(0x51a0,1.0f);putf(0x71a0,9.0f);
        putq(0x1020,a+0xc000);putq(0xc020,a+0xd000);putq(0xd018,5);
        putq(0x1050,0);assert(!configure_physics(a,&profile));putq(0x1050,a);
        assert(configure_physics(a,&profile));assert(!configure_physics(a,&profile));
        assert(enable_motion());assert(!enable_motion());
        assert(install());assert(!enable_motion());SnowDelegateOriginal cached_physics=(SnowDelegateOriginal)d[3];
        assert(submit(1)==SNOW_OBSERVATION_ACCEPTED);
        assert(cached_physics(d,owner)==UINT64_C(0xfedcba9876543210));
        SnowDelegatePhysicsObservation observed;SnowDelegateMotionObservation motion;
        assert(!collect_physics(&request,NULL));assert(!collect_physics(NULL,&observed));
        assert(!collect_state(&request,&observed,NULL));assert(!collect_state(NULL,&observed,&motion));
        assert(collect_state(&request,&observed,&motion)==SNOW_OBSERVATION_RETURNED);
        assert(motion.configured && motion.request_id==request.request_id && motion.valid_before);
        assert(motion.before.current_mode==0 && motion.before.state_observed && motion.before.child_observed);
        assert(motion.before.child_mode==5 && motion.before.ingested[0]==0);
        if(physics_mode==2 || physics_mode==5 || physics_mode==7 || physics_mode==9) {
            SnowMotionObservation zero={0};assert(!motion.valid_after && !memcmp(&motion.after,&zero,sizeof zero));
        } else {
            assert(motion.valid_after);
            if(physics_mode==6)assert(motion.after.child_mode==1 && motion.after.ingested[0]==0x3f400000);
            if(physics_mode==8)assert(!motion.after.state_observed && !motion.after.child_observed);
        }
        assert(observed.request_id==request.request_id && observed.configured);
        assert(observed.before.valid==(physics_mode==4?5u:7u));
        assert(observed.before.linear[0][0]==1.0f && observed.before.request==19 && !observed.before.substep);
        if(physics_mode==2 || physics_mode==5 || physics_mode==7) {
            SnowUpdateSnapshot zero={0};assert(!memcmp(&observed.after,&zero,sizeof zero));
        } else {
            assert(observed.after.valid==(physics_mode==4?5u:7u));
            assert(observed.after.linear[0][0]==(physics_mode==3?9.0f:2.0f));
            assert(observed.after.main_body==a+(physics_mode==3?0x7000:0x5000));
        }
        assert(!collect_physics(&request,&observed));
        if(physics_mode==6) {
            assert(submit(2)==SNOW_OBSERVATION_ACCEPTED);
            assert(cached_physics(d,owner)==UINT64_C(0xfedcba9876543210));
            assert(collect_state(&request,&observed,&motion)==SNOW_OBSERVATION_RETURNED);
            assert(motion.request_id==2 && observed.request_id==2 && request.request_id==2);
            assert(motion.valid_before && motion.valid_after && motion.before.child_mode==1);
            assert(motion.before.ingested[0]==0x3f400000 && motion.after.ingested[0]==0x3f400000);
        }
        assert(restore());assert(close_probe(NULL,NULL));
        printf("%s passed\n",argv[2]);return 0;
    }
    int requested=!strcmp(argv[2],"request");
    if(requested){assert(!arm(0));assert(arm(91)==engine);assert(!arm(92));}

    if(!strcmp(argv[2],"readonly")) {
        DWORD old;assert(VirtualProtect(owner,0x1000,PAGE_READONLY,&old));
        assert(!install());assert(restore());assert(d[3]==(uintptr_t)&invoker);
        assert(close_probe(NULL,NULL));puts("readonly passed");return 0;
    }
    if(!strcmp(argv[2],"closed")) {
        assert(close_probe(NULL,NULL));assert(!install());assert(restore());
        assert(d[3]==(uintptr_t)&invoker);puts("closed passed");return 0;
    }
    uint32_t *counts=(uint32_t *)(owner+job_offset+0x4c);
    counts[0]=3;counts[1]=0xfffffffe;counts[2]=2;counts[3]=17;counts[4]=18;counts[5]=4;
    owner[job_offset+0x194]=1;owner[0x5a]=7;
    invalidate=!strcmp(argv[2],"observation_invalid");
    assert(install());assert(!install());SnowDelegateOriginal cached=(SnowDelegateOriginal)d[3];
    if(!strcmp(argv[2],"stale_owner_before") || !strcmp(argv[2],"stale_owner_after") ||
       !strcmp(argv[2],"stale_descriptor_before") || !strcmp(argv[2],"stale_descriptor_after") ||
       !strcmp(argv[2],"identity_aba")) {
        assert(engine);assert(submit(1)==SNOW_OBSERVATION_ACCEPTED);
        int before=strstr(argv[2],"before")!=NULL;
        int descriptor=strstr(argv[2],"descriptor")!=NULL;
        int aba=!strcmp(argv[2],"identity_aba");
        if(aba){InterlockedExchangePointer((PVOID volatile *)&owner_global,NULL);
            InterlockedExchangePointer((PVOID volatile *)&owner_global,owner);}
        else if(before){if(descriptor)d[1]^=1;else owner_global=NULL;}
        else {if(descriptor)mutate_descriptor=1;else invalidate=1;}
        assert(cached(d,owner)==UINT64_C(0xfedcba9876543210));assert(calls==1);
        if(!aba)assert(!read_request(&request));
        SnowObservationReceipt outcome=collect(&request);
        assert(outcome==(aba?SNOW_OBSERVATION_RETURNED:before?SNOW_OBSERVATION_STALE_BEFORE:SNOW_OBSERVATION_STALE_AFTER));
        assert(request.request_id==1 && request.entry_tick<=request.exit_tick);
        assert(request.result==UINT64_C(0xfedcba9876543210));
        owner_global=owner;d[1]=0;invalidate=mutate_descriptor=0;
        if(!aba)assert(submit(2)==SNOW_OBSERVATION_CLOSED);
        else {assert(submit(2)==SNOW_OBSERVATION_ACCEPTED);close_requests();
            assert(collect(&request)==SNOW_OBSERVATION_CANCELLED);}
        assert(restore());assert(close_probe(NULL,NULL));
        assert(cached(d,owner)==UINT64_C(0xfedcba9876543210));assert(calls==2);
        assert(!collect(&request));printf("%s passed\n",argv[2]);return 0;
    }
    if(!strcmp(argv[2],"repeat") || !strcmp(argv[2],"cancel_pending") ||
       !strcmp(argv[2],"close_running") || !strcmp(argv[2],"competing")) {
        assert(engine);assert(submit(0)==SNOW_OBSERVATION_INVALID);
        owner_global=NULL;assert(submit(1)==SNOW_OBSERVATION_STALE_BINDING);owner_global=owner;
        if(!strcmp(argv[2],"repeat")) {
            for(uint64_t id=1;id<=32;id++) {
                assert(submit(id)==SNOW_OBSERVATION_ACCEPTED);
                assert(submit(id+1)==SNOW_OBSERVATION_BUSY);assert(!collect(&request));
                assert(cached(d,owner)==UINT64_C(0xfedcba9876543210));
                assert(submit(id+1)==SNOW_OBSERVATION_BUSY);assert(!collect(NULL));
                assert(collect(&request)==SNOW_OBSERVATION_RETURNED && request.request_id==id);
                assert(!collect(&request));assert(!read_request(&request));
                assert(submit(id)==SNOW_OBSERVATION_INVALID);
            }
            assert(calls==32);close_requests();
        } else {
            assert(submit(1)==SNOW_OBSERVATION_ACCEPTED);
            worker_callback=cached;worker_storage=d;worker_receiver=owner;
            if(!strcmp(argv[2],"cancel_pending")) {
                close_requests();assert(!read_request(&request));
                assert(cached(d,owner)==UINT64_C(0xfedcba9876543210));
                assert(collect(&request)==SNOW_OBSERVATION_CANCELLED);
                assert(request.request_id==1 && !request.entry_tick && !request.exit_tick);
            } else {
                unsigned count=!strcmp(argv[2],"competing")?8:1;HANDLE threads[8];
                if(count==1){entered_event=CreateEventA(NULL,TRUE,FALSE,NULL);release_event=CreateEventA(NULL,TRUE,FALSE,NULL);assert(entered_event&&release_event);}
                for(unsigned i=0;i<count;i++){threads[i]=CreateThread(NULL,0,invoke_worker,NULL,0,NULL);assert(threads[i]);}
                if(count==1) {
                    assert(WaitForSingleObject(entered_event,5000)==WAIT_OBJECT_0);
                    assert(!collect(&request));close_requests();assert(!close_probe(NULL,NULL));
                    assert(restore());assert(!read_request(&request));SetEvent(release_event);
                }
                assert(WaitForMultipleObjects(count,threads,TRUE,5000)==WAIT_OBJECT_0);
                for(unsigned i=0;i<count;i++)CloseHandle(threads[i]);
                assert(collect(&request)==SNOW_OBSERVATION_RETURNED && request.request_id==1);
                assert(calls==(LONG)count);close_requests();
                if(entered_event){CloseHandle(entered_event);CloseHandle(release_event);entered_event=release_event=NULL;}
            }
        }
        assert(submit(100)==SNOW_OBSERVATION_CLOSED);assert(!collect(&request));
        assert(restore());assert(close_probe(NULL,NULL));
        LONG before=calls;assert(cached(d,owner)==UINT64_C(0xfedcba9876543210));assert(calls==before+1);
        assert(!collect(&request));printf("%s passed\n",argv[2]);return 0;
    }
    assert(cached(d,owner)==UINT64_C(0xfedcba9876543210));assert(calls==1);
    if(requested&&engine){
        assert(read_request(&request));assert(request.request_id==91);
        assert(request.thread==GetCurrentThreadId() && request.entry_tick<=request.exit_tick);
        assert(request.receiver==(uintptr_t)owner && request.storage==(uintptr_t)d);
        assert(request.result==UINT64_C(0xfedcba9876543210));
        assert(!arm(92));assert(!read_request(NULL));
    }
    owner_global=owner;invalidate=0;
    if(!strcmp(argv[2],"conflict")) {
        d[3]=(uintptr_t)&competitor;assert(!restore());assert(d[3]==(uintptr_t)&competitor);
        d[3]=(uintptr_t)cached;
    }
    if(!strcmp(argv[2],"identity")) {
        owner_global=NULL;assert(!restore());assert(d[3]==(uintptr_t)cached);owner_global=owner;
        d[2]^=1;assert(!restore());assert(d[3]==(uintptr_t)cached);d[2]^=1;
    }
    assert(restore());assert(restore());assert(d[3]==(uintptr_t)&invoker);
    size_t used=0,dropped=0;assert(close_probe(&used,&dropped));assert(used==1&&dropped==0);
    assert(cached(d,owner)==UINT64_C(0xfedcba9876543210));assert(calls==2);
    assert(close_probe(&used,&dropped));assert(used==1);
    if(requested&&engine){SnowDelegateRequestObservation again;assert(read_request(&again));
        assert(!memcmp(&again,&request,sizeof request));}
    SnowDelegateRecord r;assert(read_record(0,&r,sizeof r));
    assert(r.function_storage==(uintptr_t)d && r.receiver==(uintptr_t)owner && r.result==UINT64_C(0xfedcba9876543210));
    assert(r.before.valid && r.before.executions==3 && r.before.outstanding==-2);
    assert(r.before.state==2 && r.before.started==17 && r.before.requested==18 && r.before.holds==4);
    assert(r.before.usage==1 && r.before.selector==7);
    if(!strcmp(argv[2],"observation_invalid")) {
        SnowDelegateJobState empty={0};assert(!memcmp(&r.after,&empty,sizeof empty));
    } else {
        assert(r.after.valid && r.after.requested==19 && r.after.executions==3 && r.after.outstanding==-2);
    }
    MEMORY_BASIC_INFORMATION caller_info;
    assert(r.caller && VirtualQuery((void *)r.caller,&caller_info,sizeof caller_info));
    assert(caller_info.Type==MEM_IMAGE && caller_info.AllocationBase==GetModuleHandleA(NULL));
    assert(!read_record(0,&r,sizeof r-1));assert(!read_record(1,&r,sizeof r));
    printf("%s passed\n",argv[2]);return 0;
}
