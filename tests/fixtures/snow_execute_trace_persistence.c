#define WIN32_LEAN_AND_MEAN
#include "snow_first_execute.h"
#include <assert.h>
#include <string.h>
int main(int argc,char **argv){
 assert(argc==3);
 HANDLE f=CreateFileA(argv[1],GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);assert(f!=INVALID_HANDLE_VALUE);
 HANDLE m=CreateFileMappingA(f,NULL,PAGE_READWRITE,0,sizeof(SnowFirstExecuteTrace),NULL);assert(m);CloseHandle(f);
 SnowFirstExecuteTrace *t=MapViewOfFile(m,FILE_MAP_ALL_ACCESS,0,0,0);assert(t);CloseHandle(m);
 assert(snow_first_execute_trace(t));
 if(!strcmp(argv[2],"capture")){
  unsigned char *p=VirtualAlloc(NULL,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(p);
  const unsigned char code[]={0xb8,42,0,0,0,0xc3};memcpy(p,code,sizeof code);DWORD old;
  assert(VirtualProtect(p,4096,PAGE_EXECUTE_READ,&old));assert(FlushInstructionCache(GetCurrentProcess(),p,4096));
  assert(snow_first_execute_arm(p));assert(((int (*)(void))(uintptr_t)p)()==42);
  assert(t->phase==4 && t->matched_entries==1);
 }
 assert(TerminateProcess(GetCurrentProcess(),0));return 1;
}
