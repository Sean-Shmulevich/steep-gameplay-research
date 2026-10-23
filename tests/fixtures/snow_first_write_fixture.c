#define WIN32_LEAN_AND_MEAN
#include "snow_first_write.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static volatile unsigned char *page;
static HANDLE gate;
static LONG forwarded;
static int synthetic_fault;
static LONG CALLBACK fallback(EXCEPTION_POINTERS *e){
    if(e->ExceptionRecord->ExceptionCode==0xe1234567 ||
       (synthetic_fault && e->ExceptionRecord->ExceptionCode==EXCEPTION_ACCESS_VIOLATION)){InterlockedIncrement(&forwarded);return EXCEPTION_CONTINUE_EXECUTION;}
    return EXCEPTION_CONTINUE_SEARCH;
}
static DWORD WINAPI writer(LPVOID arg){WaitForSingleObject(gate,INFINITE);page[(uintptr_t)arg]=77;return 0;}
int main(int argc,char **argv){
    assert(argc==2);page=VirtualAlloc(NULL,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);assert(page);
    SnowFirstWriteRecord r;assert(!snow_first_write_read(&r));
    if(!strcmp(argv[1],"readonly")){
        DWORD old;assert(VirtualProtect((void *)page,4096,PAGE_READONLY,&old));
        assert(!snow_first_write_arm((void *)page));
        MEMORY_BASIC_INFORMATION info;assert(VirtualQuery((void *)page,&info,sizeof info));assert(info.Protect==PAGE_READONLY);
        puts("readonly passed");return 0;
    }
    assert(snow_first_write_arm((void *)(page+64)));assert(!snow_first_write_arm((void *)page));
    assert(page[64]==0);assert(!snow_first_write_read(&r));
    AddVectoredExceptionHandler(0,fallback);RaiseException(0xe1234567,0,0,NULL);assert(forwarded==1);
    ULONG_PTR args[2]={0,(uintptr_t)page+64};synthetic_fault=1;
    RaiseException(EXCEPTION_ACCESS_VIOLATION,0,2,args); /* Read fault is not ours. */
    args[0]=1;args[1]=(uintptr_t)page+4096;
    RaiseException(EXCEPTION_ACCESS_VIOLATION,0,2,args); /* Foreign page is not ours. */
    synthetic_fault=0;assert(forwarded==3);assert(!snow_first_write_read(&r));
    if(!strcmp(argv[1],"cancel")){
        assert(snow_first_write_cancel());assert(snow_first_write_cancel());page[64]=9;
        assert(!snow_first_write_read(&r));
    }else if(!strcmp(argv[1],"concurrent")){
        HANDLE threads[16];gate=CreateEventA(NULL,TRUE,FALSE,NULL);assert(gate);
        for(unsigned i=0;i<16;i++){threads[i]=CreateThread(NULL,0,writer,(void *)(uintptr_t)i,0,NULL);assert(threads[i]);}
        assert(SetEvent(gate));assert(WaitForMultipleObjects(16,threads,TRUE,5000)==WAIT_OBJECT_0);
        for(unsigned i=0;i<16;i++){assert(page[i]==77);CloseHandle(threads[i]);}
        assert(snow_first_write_read(&r));assert(r.fault_address>=(uintptr_t)page && r.fault_address<(uintptr_t)page+16);
    }else{
        unsigned offset=!strcmp(argv[1],"neighbor")?72:64;page[offset]=55;
        assert(page[offset]==55 && snow_first_write_read(&r));assert(r.fault_address==(uintptr_t)page+offset);
        assert(r.instruction==r.context.Rip && r.thread==GetCurrentThreadId());
        uintptr_t original=r.instruction;page[64]=66;assert(snow_first_write_read(&r)&&r.instruction==original);
    }
    MEMORY_BASIC_INFORMATION info;assert(VirtualQuery((void *)page,&info,sizeof info));assert(info.Protect==PAGE_READWRITE);
    assert(snow_first_write_cancel());printf("%s passed\n",argv[1]);return 0;
}
