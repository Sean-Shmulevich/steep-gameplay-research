#define WIN32_LEAN_AND_MEAN
#include "snow_first_execute.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef LONG (WINAPI *Protect)(HANDLE,PVOID *,SIZE_T *,ULONG,PULONG);
typedef uint64_t (*Function)(void);
static Protect nt_protect;
static unsigned char *page;
static const char *mode;
static volatile LONG calls,recovered,completed;
static int context;
static HANDLE gate;
static SnowFirstExecuteTrace *trace;
static BOOL provider(void *ctx,void *address,SIZE_T size,DWORD protection,DWORD *old){
    assert(ctx==&context);InterlockedIncrement(&calls);
    int arm=protection==PAGE_READONLY;
    if((arm && !strcmp(mode,"arm_failure")) || (!arm &&
       (!strcmp(mode,"restore_failure") || !strcmp(mode,"cancel_failure")))){
        SetLastError(ERROR_ACCESS_DENIED);return FALSE;
    }
    if((arm && !strcmp(mode,"arm_lie")) || (!arm && !strcmp(mode,"restore_lie")))return TRUE;
    PVOID p=address;SIZE_T n=size;LONG status=nt_protect(GetCurrentProcess(),&p,&n,protection,old);
    if(status<0){SetLastError(ERROR_ACCESS_DENIED);return FALSE;}
    if(arm && !strcmp(mode,"arm_race"))assert(((Function)(uintptr_t)page)()==42);
    return TRUE;
}
static LONG CALLBACK recovery(EXCEPTION_POINTERS *e){
    if(e->ExceptionRecord->ExceptionCode==EXCEPTION_ACCESS_VIOLATION &&
       e->ExceptionRecord->NumberParameters>=2 && e->ExceptionRecord->ExceptionInformation[0]==8 &&
       e->ContextRecord->Rip==(uintptr_t)page &&
       (!strcmp(mode,"restore_failure") || !strcmp(mode,"restore_lie"))){
        DWORD old;assert(VirtualProtect(page,4096,PAGE_EXECUTE_READ,&old));
        InterlockedIncrement(&recovered);return EXCEPTION_CONTINUE_EXECUTION;
    }
    return EXCEPTION_CONTINUE_SEARCH;
}
static DWORD WINAPI caller(LPVOID ignored){
    (void)ignored;WaitForSingleObject(gate,INFINITE);assert(((Function)(uintptr_t)page)()==42);
    InterlockedIncrement(&completed);return 0;
}
int main(int argc,char **argv){
    assert(argc==2 || argc==3);mode=argv[1];
    assert(!snow_first_execute_trace(NULL));
    trace=VirtualAlloc(NULL,sizeof *trace,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);assert(trace);
    assert(snow_first_execute_trace(trace) && trace->version==2);
    nt_protect=(Protect)(uintptr_t)GetProcAddress(GetModuleHandleA("ntdll.dll"),"NtProtectVirtualMemory");assert(nt_protect);
    const unsigned char code[]={0xb8,42,0,0,0,0xc3},neighbor[]={0xb8,99,0,0,0,0xc3};
    if(argc==3){
        HMODULE dll=LoadLibraryA(argv[2]);assert(dll);page=(void *)GetProcAddress(dll,"snow_execute_target");
        assert(page && !((uintptr_t)page%4096));assert((void *)GetProcAddress(dll,"snow_execute_neighbor")==page+64);
    }else{
        page=VirtualAlloc(NULL,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);assert(page);
        memcpy(page,code,sizeof code);memcpy(page+64,neighbor,sizeof neighbor);
    }
    DWORD old;assert(VirtualProtect(page,4096,PAGE_EXECUTE_READ,&old));assert(FlushInstructionCache(GetCurrentProcess(),page,4096));
    if(!strcmp(mode,"warm"))for(unsigned i=0;i<1000;i++)assert(((Function)(uintptr_t)page)()==42);
    assert(!snow_first_execute_backend(NULL,NULL));
    assert(snow_first_execute_backend(provider,!strcmp(mode,"overlap")?page:(void *)&context));
    assert(AddVectoredExceptionHandler(0,recovery));
    int armed=snow_first_execute_arm(page);unsigned stage;DWORD error;
    assert(!snow_first_execute_trace(trace));
    snow_first_execute_arm_diagnostic(&stage,&error);SnowFirstExecuteRecord record;
    if(!strcmp(mode,"overlap") || !strcmp(mode,"arm_failure") || !strcmp(mode,"arm_lie")){
        assert(!armed && !snow_first_execute_read(&record));
        assert(stage==(!strcmp(mode,"overlap")?2u:5u));
        if(!strcmp(mode,"arm_failure"))assert(error==ERROR_ACCESS_DENIED);
        if(!strcmp(mode,"arm_lie"))assert(error==ERROR_INVALID_DATA);
        MEMORY_BASIC_INFORMATION info;assert(VirtualQuery(page,&info,sizeof info) && info.Protect==PAGE_EXECUTE_READ);
        printf("%s refused calls=%ld\n",mode,calls);return 0;
    }
    assert(armed && !snow_first_execute_backend(provider,&context));
    if(!strcmp(mode,"cancel") || !strcmp(mode,"cancel_failure")){
        int cancelled=snow_first_execute_cancel();assert(cancelled==!strcmp(mode,"cancel"));
        if(!cancelled){assert(VirtualProtect(page,4096,PAGE_EXECUTE_READ,&old));assert(!snow_first_execute_cancel());}
        assert(!snow_first_execute_read(&record));
    }else if(!strcmp(mode,"concurrent")){
        HANDLE threads[16];DWORD ids[16];gate=CreateEventA(NULL,TRUE,FALSE,NULL);assert(gate);
        for(unsigned i=0;i<16;i++){threads[i]=CreateThread(NULL,0,caller,NULL,0,&ids[i]);assert(threads[i]);}
        assert(SetEvent(gate));assert(WaitForMultipleObjects(16,threads,TRUE,5000)==WAIT_OBJECT_0 && completed==16);
        assert(snow_first_execute_read(&record));int member=0;
        for(unsigned i=0;i<16;i++){member|=record.thread==ids[i];CloseHandle(threads[i]);}assert(member);CloseHandle(gate);
    }else{
        int adjacent=!strcmp(mode,"neighbor");assert(((Function)(uintptr_t)(page+(adjacent?64:0)))()==(adjacent?99u:42u));
        if(!strcmp(mode,"restore_failure") || !strcmp(mode,"restore_lie")){
            assert(recovered==1 && !snow_first_execute_read(&record) && !snow_first_execute_cancel());
        }else{
            assert(snow_first_execute_read(&record) && record.instruction==(uintptr_t)(page+(adjacent?64:0)));
            assert(record.stack_valid && snow_first_execute_cancel());
        }
    }
    assert(calls==2);assert(((Function)(uintptr_t)page)()==42);
    if(!strcmp(mode,"cancel") || !strcmp(mode,"cancel_failure")){
        assert(trace->phase==0 && trace->matched_entries==0);
    }else{
        assert(trace->handler_entries>=trace->matched_entries && trace->matched_entries>=1);
        int failed=!strcmp(mode,"restore_failure") || !strcmp(mode,"restore_lie");
        assert(trace->phase==(failed?5:4));
        assert(trace->restore_error==(failed?(!strcmp(mode,"restore_failure")?ERROR_ACCESS_DENIED:ERROR_INVALID_DATA):0));
    }
    MEMORY_BASIC_INFORMATION info;assert(VirtualQuery(page,&info,sizeof info) && info.Protect==PAGE_EXECUTE_READ);
    assert(!memcmp(page,code,sizeof code) && !memcmp(page+64,neighbor,sizeof neighbor));
    printf("%s passed calls=%ld recovered=%ld\n",mode,calls,recovered);return 0;
}
