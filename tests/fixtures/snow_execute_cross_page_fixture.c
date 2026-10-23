#define WIN32_LEAN_AND_MEAN
#include "snow_first_execute.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned char *page;
static LONG recovered;
static LONG CALLBACK recovery(EXCEPTION_POINTERS *e){
    if(e->ExceptionRecord->ExceptionCode==EXCEPTION_ACCESS_VIOLATION &&
       e->ExceptionRecord->NumberParameters>=2 && e->ExceptionRecord->ExceptionInformation[0]==8 &&
       e->ExceptionRecord->ExceptionInformation[1]==(uintptr_t)page &&
       e->ContextRecord->Rip==(uintptr_t)page-2){
        DWORD old;assert(VirtualProtect(page,4096,PAGE_EXECUTE_READ,&old));
        recovered++;return EXCEPTION_CONTINUE_EXECUTION;
    }
    return EXCEPTION_CONTINUE_SEARCH;
}
int main(int argc,char **argv){
    assert(argc==2);int expect_match=!strcmp(argv[1],"match");
    unsigned char *allocation=VirtualAlloc(NULL,8192,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);assert(allocation);
    page=allocation+4096;
    /* Authored three-byte mov rax,rax crosses the page; then return 42. */
    const unsigned char code[]={0x48,0x89,0xc0,0xb8,42,0,0,0,0xc3};
    memcpy(page-2,code,sizeof code);DWORD old;
    assert(VirtualProtect(allocation,8192,PAGE_EXECUTE_READ,&old));
    assert(FlushInstructionCache(GetCurrentProcess(),allocation,8192));
    SnowFirstExecuteTrace *trace=VirtualAlloc(NULL,sizeof *trace,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);assert(trace);
    assert(snow_first_execute_trace(trace));assert(AddVectoredExceptionHandler(0,recovery));
    assert(snow_first_execute_arm(page));assert(((int (*)(void))(uintptr_t)(page-2))()==42);
    SnowFirstExecuteRecord r;int captured=snow_first_execute_read(&r);
    assert(captured==expect_match && recovered==!expect_match);
    assert(trace->exceptions[0].reason==(expect_match?0u:7u));
    if(captured){assert(r.instruction==(uintptr_t)page-2 && r.fault_address==(uintptr_t)page);assert(snow_first_execute_cancel());}
    MEMORY_BASIC_INFORMATION info;assert(VirtualQuery(page,&info,sizeof info) && info.Protect==PAGE_EXECUTE_READ);
    printf("captured=%d fixture_recovery=%ld reason=%llu\n",captured,recovered,(unsigned long long)trace->exceptions[0].reason);
    return 0;
}
