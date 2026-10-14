#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#pragma pack(push,1)
struct Marker {DWORD magic,pid;FILETIME created;uintptr_t module;};
#pragma pack(pop)
BOOL WINAPI LoaderEntry(HINSTANCE h,DWORD reason,LPVOID unused){
 (void)unused;if(reason!=DLL_PROCESS_ATTACH)return TRUE;
 WCHAR path[MAX_PATH];DWORD n=GetModuleFileNameW(h,path,MAX_PATH);
 if(!n||n>=MAX_PATH)return FALSE;
 while(n&&path[n-1]!=L'\\')n--;
 const WCHAR name[]=L"snow_late_probe.bin";
 if(n+sizeof(name)/sizeof(WCHAR)>MAX_PATH)return FALSE;
 for(DWORD i=0;i<sizeof(name)/sizeof(WCHAR);i++)path[n+i]=name[i];
 struct Marker m={0};FILETIME e,k,u;m.magic=0x4c415445;m.pid=GetCurrentProcessId();m.module=(uintptr_t)h;
 if(!GetProcessTimes(GetCurrentProcess(),&m.created,&e,&k,&u))return FALSE;
 HANDLE f=CreateFileW(path,GENERIC_WRITE,FILE_SHARE_READ,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
 if(f==INVALID_HANDLE_VALUE)return FALSE;
 DWORD wrote=0;BOOL ok=WriteFile(f,&m,sizeof(m),&wrote,NULL);CloseHandle(f);
 return ok&&wrote==sizeof(m);
}
