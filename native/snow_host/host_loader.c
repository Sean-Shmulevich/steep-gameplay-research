/* Late-load snow_host.dll into a verified process, then start it outside
 * DllMain by running its SnowHost_Start export on a second remote thread.
 * Usage: host_loader.exe <pid> <creation_filetime_hex> <absolute snow_host.dll path> <port>
 * Same guards as ../mod_loader/load_probe.c, plus export verification. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <wchar.h>
#ifndef SNOW_REMOTE_TIMEOUT_MS
#define SNOW_REMOTE_TIMEOUT_MS 5000
#endif
static const WCHAR *base(const WCHAR *s){const WCHAR *p=wcsrchr(s,L'\\');return p?p+1:s;}
static BOOL module(DWORD pid,const WCHAR *name,MODULEENTRY32W *m){
 HANDLE snap=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32,pid);
 if(snap==INVALID_HANDLE_VALUE)return FALSE;
 m->dwSize=sizeof(*m);BOOL found=FALSE;
 if(Module32FirstW(snap,m))do{if(!_wcsicmp(m->szModule,name)){found=TRUE;break;}}while(Module32NextW(snap,m));
 CloseHandle(snap);return found;
}
/* Run a remote thread at entry with param; verify 16 entry bytes against the local copy first. */
static int remote_call(HANDLE p,uintptr_t entry,const BYTE *local,LPVOID param,DWORD *code,BOOL *completed){
 BYTE bytes[16];SIZE_T read=0;
 if(!ReadProcessMemory(p,(LPCVOID)entry,bytes,sizeof(bytes),&read)||read!=sizeof(bytes)||memcmp(bytes,local,16))return 0;
 HANDLE t=CreateRemoteThread(p,NULL,0,(LPTHREAD_START_ROUTINE)entry,param,0,NULL);if(!t)return 0;
 DWORD wait=WaitForSingleObject(t,SNOW_REMOTE_TIMEOUT_MS);
 *completed=wait==WAIT_OBJECT_0;
 if(*completed)GetExitCodeThread(t,code);
 CloseHandle(t);return *completed;
}
int wmain(int argc,WCHAR **argv){
 HANDLE p=NULL;LPVOID remote=NULL;BOOL completed=FALSE,started=FALSE;int rc=2;const char *stage="arguments";DWORD code=0xffffffff;
 MODULEENTRY32W loaded;
 if(argc!=5)goto done;
 DWORD pid=wcstoul(argv[1],NULL,10);unsigned long long expected=wcstoull(argv[2],NULL,16);unsigned long port=wcstoul(argv[4],NULL,10);
 if(!pid||!expected||port<1024||port>65535||_wcsicmp(base(argv[3]),L"snow_host.dll")||wcslen(argv[3])>=MAX_PATH||GetFileAttributesW(argv[3])==INVALID_FILE_ATTRIBUTES)goto done;
 stage="open";p=OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ|PROCESS_VM_WRITE|PROCESS_VM_OPERATION|PROCESS_CREATE_THREAD,FALSE,pid);if(!p)goto done;
 FILETIME c,e,k,u;WCHAR path[MAX_PATH];DWORD len=MAX_PATH;
 stage="identity";
 if(!GetProcessTimes(p,&c,&e,&k,&u)||((((unsigned long long)c.dwHighDateTime<<32)|c.dwLowDateTime)!=expected)||!QueryFullProcessImageNameW(p,0,path,&len))goto done;
 if(_wcsicmp(base(path),L"steep.exe")&&_wcsicmp(base(path),L"late_fixture.exe"))goto done;
 if(module(pid,L"snow_host.dll",&loaded)){stage="already_loaded";goto done;}
 stage="loader_identity";
 FARPROC loader=GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"LoadLibraryW");HMODULE owner=NULL;
 if(!loader||!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCWSTR)(uintptr_t)loader,&owner))goto done;
 if(!GetModuleFileNameW(owner,path,MAX_PATH))goto done;
 MODULEENTRY32W target;if(!module(pid,base(path),&target))goto done;
 uintptr_t offset=(uintptr_t)loader-(uintptr_t)owner;if(offset+16>target.modBaseSize)goto done;
 stage="export_identity";
 HMODULE local=LoadLibraryExW(argv[3],NULL,DONT_RESOLVE_DLL_REFERENCES);if(!local)goto done;
 FARPROC start=GetProcAddress(local,"SnowHost_Start");if(!start)goto done;
 uintptr_t start_rva=(uintptr_t)start-(uintptr_t)local;
 stage="path_allocation";SIZE_T size=(wcslen(argv[3])+1)*sizeof(WCHAR),wrote=0;
 remote=VirtualAllocEx(p,NULL,size,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!remote)goto done;
 if(!WriteProcessMemory(p,remote,argv[3],size,&wrote)||wrote!=size)goto done;
 stage="load_thread";
 if(!remote_call(p,(uintptr_t)target.modBaseAddr+offset,(const BYTE*)(uintptr_t)loader,remote,&code,&completed))goto done;
 stage="module_verification";if(!module(pid,L"snow_host.dll",&loaded)||_wcsicmp(loaded.szExePath,argv[3])||start_rva+16>loaded.modBaseSize)goto done;
 stage="start_thread";BOOL start_done=FALSE;
 if(!remote_call(p,(uintptr_t)loaded.modBaseAddr+start_rva,(const BYTE*)(uintptr_t)start,(LPVOID)(uintptr_t)port,&code,&start_done)){completed=start_done;goto done;}
 started=TRUE;
 if(code!=0){stage="start_result";goto done;}
 printf("{\"ok\":true,\"pid\":%lu,\"module\":\"0x%llx\",\"port\":%lu}\n",pid,(unsigned long long)(uintptr_t)loaded.modBaseAddr,port);rc=0;
done:
 if(rc)printf("{\"ok\":false,\"stage\":\"%s\",\"winerror\":%lu,\"thread_completed\":%s,\"started\":%s,\"start_code\":%lu}\n",stage,GetLastError(),completed?"true":"false",started?"true":"false",code);
 // A timed-out load thread may still need its path buffer. Never free that buffer or terminate the thread.
 if(remote&&completed)VirtualFreeEx(p,remote,0,MEM_RELEASE);
 if(p)CloseHandle(p);
 return rc;
}
