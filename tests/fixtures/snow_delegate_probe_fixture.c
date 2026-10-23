#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "snow_delegate_probe.h"
static void *owner_global,*expected_receiver;
static uintptr_t table[16];
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
