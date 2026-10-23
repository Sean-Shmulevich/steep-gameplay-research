#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "snow_delegate_probe.h"
static void *owner_global;
static uintptr_t table[16];
static unsigned calls;
static int invalidate;
static unsigned job_offset=0x218;
static uintptr_t body(void *receiver) { assert(receiver==owner_global);calls++;
    ((uint32_t *)((unsigned char *)receiver+job_offset+0x4c))[4]++;
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
    assert(abi()==3 && record_size()==sizeof(SnowDelegateRecord));
    owner_global=VirtualAlloc(NULL,0x1000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(owner_global);
    unsigned char *owner=owner_global;table[0x40/8]=(uintptr_t)&dispatch_method;
    *(uintptr_t *)(owner+job_offset)=(uintptr_t)table;
    uintptr_t *d=(uintptr_t *)(owner+job_offset+0x198);
    d[0]=(uintptr_t)&body;d[1]=0;d[2]=(uintptr_t)owner|2;d[3]=(uintptr_t)&invoker;
    SnowDelegateBinding b={(uintptr_t)&owner_global,(uintptr_t)owner,(uintptr_t)table,
        (uintptr_t)&dispatch_method,d[0],d[1],d[2],d[3]};
    assert(!configure_site(&b,(SnowDelegateSite)99));
    assert(engine?configure_site(&b,SNOW_DELEGATE_ENGINE_MAIN):configure(&b));
    assert(!configure(&b));
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
    assert(cached(d,owner)==UINT64_C(0xfedcba9876543210));assert(calls==1);
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
