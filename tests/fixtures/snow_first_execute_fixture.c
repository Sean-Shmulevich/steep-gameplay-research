#define WIN32_LEAN_AND_MEAN
#include "snow_first_execute.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef uint64_t (*Function)(void);
static Function target;
static HANDLE gate;
static volatile LONG completed, forwarded;
static LONG CALLBACK fallback(EXCEPTION_POINTERS *e){
    if(e->ExceptionRecord->ExceptionCode==EXCEPTION_ACCESS_VIOLATION){
        InterlockedIncrement(&forwarded);return EXCEPTION_CONTINUE_EXECUTION;
    }
    return EXCEPTION_CONTINUE_SEARCH;
}
static DWORD WINAPI caller(LPVOID unused){
    (void)unused;WaitForSingleObject(gate,INFINITE);
    assert(target()==42);InterlockedIncrement(&completed);return 0;
}
int main(int argc,char **argv){
    assert(argc==2 || argc==3);
    unsigned char *page;
    /* Authored x64 functions: mov eax,42; ret and mov eax,99; ret. */
    const unsigned char a[]={0xb8,42,0,0,0,0xc3},b[]={0xb8,99,0,0,0,0xc3};
    if(argc==3){
        HMODULE dll=LoadLibraryA(argv[2]);assert(dll);
        page=(void *)GetProcAddress(dll,"snow_execute_target");assert(page && !((uintptr_t)page%4096));
        assert((void *)GetProcAddress(dll,"snow_execute_neighbor")==page+64);
        MEMORY_BASIC_INFORMATION info;assert(VirtualQuery(page,&info,sizeof info) && info.Type==MEM_IMAGE);
    }else{
        page=VirtualAlloc(NULL,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);assert(page);
        memcpy(page,a,sizeof a);memcpy(page+64,b,sizeof b);
    }
    target=(Function)(uintptr_t)page;Function neighbor=(Function)(uintptr_t)(page+64);
    DWORD old;assert(VirtualProtect(page,4096,PAGE_EXECUTE_READ,&old));
    assert(FlushInstructionCache(GetCurrentProcess(),page,4096));
    SnowFirstExecuteRecord r;assert(!snow_first_execute_read(&r));
    if(!strcmp(argv[1],"self")){
        assert(!snow_first_execute_arm((void *)(uintptr_t)&caller));puts("self passed");return 0;
    }
    if(!strcmp(argv[1],"rw") || !strcmp(argv[1],"rwx")){
        DWORD protection=!strcmp(argv[1],"rw")?PAGE_READWRITE:PAGE_EXECUTE_READWRITE;
        assert(VirtualProtect(page,4096,protection,&old));
        MEMORY_BASIC_INFORMATION before,info;assert(VirtualQuery(page,&before,sizeof before));
        assert(before.Protect==protection || (argc==3 && before.Protect==
            (protection==PAGE_READWRITE?PAGE_WRITECOPY:PAGE_EXECUTE_WRITECOPY)));
        assert(!snow_first_execute_arm(page));
        assert(VirtualQuery(page,&info,sizeof info));assert(info.Protect==before.Protect);
        printf("protection refusal passed requested=%lu observed=%lu\n",
            (unsigned long)protection,(unsigned long)info.Protect);return 0;
    }
    if(!strcmp(argv[1],"warm"))for(int i=0;i<1000;i++)assert(target()==42);
    assert(snow_first_execute_arm(page));assert(!snow_first_execute_arm(page));
    assert(page[0]==0xb8 && !snow_first_execute_read(&r));
    AddVectoredExceptionHandler(0,fallback);
    ULONG_PTR args[2]={0,(uintptr_t)page};RaiseException(EXCEPTION_ACCESS_VIOLATION,0,2,args);
    args[0]=1;RaiseException(EXCEPTION_ACCESS_VIOLATION,0,2,args);
    args[0]=8;args[1]=(uintptr_t)page+4096;RaiseException(EXCEPTION_ACCESS_VIOLATION,0,2,args);
    assert(forwarded==3 && !snow_first_execute_read(&r));
    if(!strcmp(argv[1],"cancel")){
        assert(snow_first_execute_cancel());assert(target()==42);assert(!snow_first_execute_read(&r));
    }else{
        uintptr_t expected=(uintptr_t)page;
        if(!strcmp(argv[1],"concurrent")){
            HANDLE threads[16];gate=CreateEventA(NULL,TRUE,FALSE,NULL);assert(gate);
            for(int i=0;i<16;i++){threads[i]=CreateThread(NULL,0,caller,NULL,0,NULL);assert(threads[i]);}
            assert(SetEvent(gate));assert(WaitForMultipleObjects(16,threads,TRUE,5000)==WAIT_OBJECT_0);
            assert(completed==16);for(int i=0;i<16;i++)CloseHandle(threads[i]);CloseHandle(gate);
        }else if(!strcmp(argv[1],"neighbor")){assert(neighbor()==99);expected+=64;}
        else assert(target()==42);
        assert(snow_first_execute_read(&r));assert(r.instruction==expected && r.fault_address==expected);
        assert(r.context.Rip==expected && r.stack_valid && r.tick && r.thread);
        uint64_t return_candidate;memcpy(&return_candidate,r.stack,8);assert(return_candidate);
        assert(target()==42 && neighbor()==99);SnowFirstExecuteRecord after;
        assert(snow_first_execute_read(&after) && !memcmp(&r,&after,sizeof r));
    }
    assert(snow_first_execute_cancel());MEMORY_BASIC_INFORMATION info;
    assert(VirtualQuery(page,&info,sizeof info) && info.Protect==PAGE_EXECUTE_READ);
    assert(!memcmp(page,a,sizeof a) && !memcmp(page+64,b,sizeof b));
    printf("%s passed\n",argv[1]);return 0;
}
