#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "snow_finalizer_probe.h"
static void *owner_global;
static uintptr_t table[512] __attribute__((section(".sntab"),aligned(4096)));
static unsigned calls;
static int invalidate;
static uintptr_t original(void *job) {
    calls++;*(uint32_t *)((unsigned char *)job+0x54)=0;
    if(invalidate)owner_global=NULL;
    return UINT64_C(0xfedcba9876543210);
}
static uintptr_t competitor(void *job) { (void)job;return 5; }
static void replace(uintptr_t value) {
    DWORD old,ignored;assert(VirtualProtect(table,sizeof table,PAGE_READWRITE,&old));
    table[0x70/8]=value;assert(VirtualProtect(table,sizeof table,old,&ignored));
}
int main(int argc,char **argv) {
    assert(argc==3);HMODULE dll=LoadLibraryA(argv[1]);assert(dll);
    int (*configure)(const SnowFinalizerBinding *)=(void *)GetProcAddress(dll,"SnowFinalizerProbe_Configure");
    int (*install)(void)=(void *)GetProcAddress(dll,"SnowFinalizerProbe_Install");
    int (*restore)(void)=(void *)GetProcAddress(dll,"SnowFinalizerProbe_Restore");
    int (*close_probe)(size_t *,size_t *)=(void *)GetProcAddress(dll,"SnowFinalizerProbe_Close");
    int (*read_record)(size_t,void *,size_t)=(void *)GetProcAddress(dll,"SnowFinalizerProbe_Read");
    size_t (*record_size)(void)=(void *)GetProcAddress(dll,"SnowFinalizerProbe_RecordSize");
    uint32_t (*abi)(void)=(void *)GetProcAddress(dll,"SnowFinalizerProbe_ABIVersion");
    assert(configure&&install&&restore&&close_probe&&read_record&&record_size&&abi);
    assert(abi()==1&&record_size()==sizeof(SnowDelegateRecord));
    unsigned char *owner=VirtualAlloc(NULL,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(owner);
    unsigned char *other=VirtualAlloc(NULL,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(other);
    owner_global=owner;void *job=owner+0x218;
    *(uintptr_t *)job=(uintptr_t)table;*(uintptr_t *)other=(uintptr_t)table;
    table[0x70/8]=(uintptr_t)&original;
    SnowFinalizerBinding b={(uintptr_t)&owner_global,(uintptr_t)owner,(uintptr_t)table,(uintptr_t)&original};
    if(!strcmp(argv[2],"heap_table")) {
        uintptr_t *heap=VirtualAlloc(NULL,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(heap);
        heap[0x70/8]=(uintptr_t)&original;*(uintptr_t *)job=(uintptr_t)heap;b.job_table=(uintptr_t)heap;
        assert(!configure(&b));puts("heap_table refused");return 0;
    }
    assert(configure(&b));assert(!configure(&b));
    if(!strcmp(argv[2],"closed")) {
        assert(close_probe(NULL,NULL));assert(!install());assert(restore()==1);
        assert(table[0x70/8]==(uintptr_t)&original);puts("closed passed");return 0;
    }
    if(!strcmp(argv[2],"identity_before")) {
        owner_global=NULL;assert(!install());assert(restore()==1);
        assert(table[0x70/8]==(uintptr_t)&original);puts("identity_before passed");return 0;
    }
    MEMORY_BASIC_INFORMATION m;assert(VirtualQuery(table,&m,sizeof m));
    DWORD expected=m.Protect;
    if(!strcmp(argv[2],"readonly")) {
        DWORD old;assert(VirtualProtect(table,sizeof table,PAGE_READONLY,&old));expected=PAGE_READONLY;
    }
    assert(install()==1);assert(!install());
    assert(VirtualQuery(table,&m,sizeof m));assert(m.Protect==expected);
    SnowFinalizerOriginal cached=(SnowFinalizerOriginal)table[0x70/8];
    assert(cached(other)==UINT64_C(0xfedcba9876543210));
    uint32_t *c=(uint32_t *)((unsigned char *)job+0x4c);
    c[0]=0;c[1]=1;c[2]=2;c[3]=17;c[4]=17;c[5]=0;owner[0x5a]=7;
    invalidate=!strcmp(argv[2],"identity_during");
    assert(cached(job)==UINT64_C(0xfedcba9876543210));assert(calls==2);invalidate=0;
    if(!strcmp(argv[2],"conflict")) {
        replace((uintptr_t)&competitor);assert(restore()==0);assert(table[0x70/8]==(uintptr_t)&competitor);
        replace((uintptr_t)cached);
    }
    /* Restoring the pinned image slot must work even after owner identity loss. */
    assert(restore()==1);assert(restore()==1);assert(table[0x70/8]==(uintptr_t)&original);
    assert(VirtualQuery(table,&m,sizeof m));assert(m.Protect==expected);
    size_t used=0,dropped=0;assert(close_probe(&used,&dropped));assert(used==1&&dropped==0);
    owner_global=owner;
    assert(cached(job)==UINT64_C(0xfedcba9876543210));assert(cached(other)==UINT64_C(0xfedcba9876543210));
    assert(calls==4);assert(close_probe(&used,&dropped));assert(used==1);
    SnowDelegateRecord r;assert(read_record(0,&r,sizeof r));
    assert(r.function_storage==0&&r.receiver==(uintptr_t)job&&r.result==UINT64_C(0xfedcba9876543210));
    assert(r.before.valid&&r.before.executions==0&&r.before.outstanding==1&&r.before.state==2);
    assert(r.before.started==17&&r.before.requested==17&&r.before.selector==7);
    if(!strcmp(argv[2],"identity_during")) {
        SnowDelegateJobState empty={0};assert(!memcmp(&r.after,&empty,sizeof empty));
    } else assert(r.after.valid&&r.after.outstanding==1&&r.after.state==0);
    assert(r.caller&&VirtualQuery((void *)r.caller,&m,sizeof m));
    assert(m.Type==MEM_IMAGE&&m.AllocationBase==GetModuleHandleA(NULL));
    SnowDelegateRecord before=r;assert(!read_record(0,&r,sizeof r-1));assert(!memcmp(&r,&before,sizeof r));
    assert(!read_record(1,&r,sizeof r));printf("%s passed\n",argv[2]);return 0;
}
