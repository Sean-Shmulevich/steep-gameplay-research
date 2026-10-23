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
    assert(argc==2 || argc==3);int image=argc==3;DWORD original=PAGE_READWRITE;
    if(image){
        HMODULE dll=LoadLibraryA(argv[2]);assert(dll);
        page=(void *)GetProcAddress(dll,"snow_fixture_page");assert(page && !((uintptr_t)page%4096));
        MEMORY_BASIC_INFORMATION info;assert(VirtualQuery((void *)page,&info,sizeof info));assert(info.Type==MEM_IMAGE);
        DWORD old;assert(VirtualProtect((void *)page,4096,PAGE_WRITECOPY,&old));original=PAGE_WRITECOPY;
    }else {
        page=VirtualAlloc(NULL,8192,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);assert(page);
        DWORD old;assert(VirtualProtect((void *)(page+4096),4096,PAGE_NOACCESS,&old));
    }
    assert(page);
    SnowFirstWriteRecord r;assert(!snow_first_write_read(&r));
    SnowWriteWindowSpec specs[]={{SNOW_WRITE_FAULT,0,8},{SNOW_WRITE_RSP,0,16},{SNOW_WRITE_FAULT,4096,8}};
    assert(!snow_first_write_windows(specs,4));assert(!snow_first_write_windows(NULL,1));
    SnowWriteWindowSpec bad={SNOW_WRITE_RBP,-4097,8};assert(!snow_first_write_windows(&bad,1));
    bad.offset=0;bad.size=129;assert(!snow_first_write_windows(&bad,1));
    assert(snow_first_write_windows(specs,3));
    if(!strcmp(argv[1],"readonly")){
        DWORD old;assert(VirtualProtect((void *)page,4096,PAGE_READONLY,&old));
        assert(!snow_first_write_arm((void *)page));
        MEMORY_BASIC_INFORMATION info;assert(VirtualQuery((void *)page,&info,sizeof info));assert(info.Protect==PAGE_READONLY);
        puts("readonly passed");return 0;
    }
    assert(snow_first_write_arm((void *)(page+64)));assert(!snow_first_write_arm((void *)page));assert(!snow_first_write_windows(specs,3));
    assert(page[64]==0);assert(!snow_first_write_read(&r));
    AddVectoredExceptionHandler(0,fallback);RaiseException(0xe1234567,0,0,NULL);assert(forwarded==1);
    ULONG_PTR args[2]={0,(uintptr_t)page+64};synthetic_fault=1;
    RaiseException(EXCEPTION_ACCESS_VIOLATION,0,2,args); /* Read fault is not ours. */
    args[0]=1;args[1]=(uintptr_t)page+4096;
    RaiseException(EXCEPTION_ACCESS_VIOLATION,0,2,args); /* Foreign page is not ours. */
    synthetic_fault=0;assert(forwarded==3);assert(!snow_first_write_read(&r));
    if(!strcmp(argv[1],"cancel")){
        assert(snow_first_write_cancel());assert(snow_first_write_cancel());
        MEMORY_BASIC_INFORMATION before;assert(VirtualQuery((void *)page,&before,sizeof before));assert(before.Protect==original);
        page[64]=9;
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
    if(strcmp(argv[1],"cancel")){
        assert(snow_first_write_read(&r) && r.window_count==3);
        assert(r.windows[0].valid && r.windows[0].address==r.fault_address);
        assert(r.windows[0].bytes[0]!=55 && r.windows[0].bytes[0]!=77);
        assert(r.windows[1].valid && r.windows[1].address==r.context.Rsp);
        if(!image){unsigned char zero[128]={0};assert(!r.windows[2].valid && !memcmp(r.windows[2].bytes,zero,128));}
    }
    MEMORY_BASIC_INFORMATION info;assert(VirtualQuery((void *)page,&info,sizeof info));assert(info.Protect==original || (image && info.Protect==PAGE_READWRITE));
    assert(snow_first_write_cancel());printf("%s %s passed original=%lu final=%lu\n",image?"image":"private",argv[1],(unsigned long)original,(unsigned long)info.Protect);return 0;
}
