#define WIN32_LEAN_AND_MEAN
#include "snow_first_execute.h"
#include <assert.h>
#include <string.h>
static LONG CALLBACK consume(EXCEPTION_POINTERS *e){
 return e->ExceptionRecord->ExceptionCode==0xe0424242?EXCEPTION_CONTINUE_EXECUTION:EXCEPTION_CONTINUE_SEARCH;
}
int main(int argc,char **argv){
 assert(argc==3);
 HANDLE f=CreateFileA(argv[1],GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);assert(f!=INVALID_HANDLE_VALUE);
 HANDLE m=CreateFileMappingA(f,NULL,PAGE_READWRITE,0,sizeof(SnowFirstExecuteTrace),NULL);assert(m);CloseHandle(f);
 SnowFirstExecuteTrace *t=MapViewOfFile(m,FILE_MAP_ALL_ACCESS,0,0,0);assert(t);CloseHandle(m);
 assert(snow_first_execute_trace(t));
 if(strcmp(argv[2],"idle")){
  unsigned char *p=VirtualAlloc(NULL,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(p);
  const unsigned char code[]={0xb8,42,0,0,0,0xc3};memcpy(p,code,sizeof code);DWORD old;
  assert(VirtualProtect(p,4096,PAGE_EXECUTE_READ,&old));assert(FlushInstructionCache(GetCurrentProcess(),p,4096));
  assert(AddVectoredExceptionHandler(0,consume));assert(snow_first_execute_arm(p));
  if(!strcmp(argv[2],"capture")){
   assert(((int (*)(void))(uintptr_t)p)()==42);
   assert(t->phase==4 && t->matched_entries==1 && t->exceptions[0].reason==0);
  }else{
   unsigned count=!strcmp(argv[2],"overflow")?10:1;ULONG_PTR params[]={0x1234,0x5678};
   for(unsigned i=0;i<count;i++)RaiseException(0xe0424242,0,2,params);
   assert(t->handler_entries==(LONG)count && t->matched_entries==0 && t->phase==0);
   for(unsigned i=0;i<(count<8?count:8);i++){
    assert(t->exceptions[i].published==1 && t->exceptions[i].reason==2);
    assert(t->exceptions[i].code==0xe0424242 && t->exceptions[i].parameter_count==2);
    assert(t->exceptions[i].operation==params[0] && t->exceptions[i].address==params[1]);
   }
   assert(snow_first_execute_cancel());
  }
 }
 assert(TerminateProcess(GetCurrentProcess(),0));return 1;
}
