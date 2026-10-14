#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <wchar.h>
static const WCHAR *base(const WCHAR *s){const WCHAR *p=wcsrchr(s,L'\\');return p?p+1:s;}
static BOOL module(DWORD pid,const WCHAR *name,MODULEENTRY32W *m){
 HANDLE snap=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32,pid);
 if(snap==INVALID_HANDLE_VALUE)return FALSE;
 m->dwSize=sizeof(*m);BOOL found=FALSE;
 if(Module32FirstW(snap,m))do{if(!_wcsicmp(m->szModule,name)){found=TRUE;break;}}while(Module32NextW(snap,m));
 CloseHandle(snap);return found;
}
int wmain(int argc,WCHAR **argv){
 HANDLE p=NULL,t=NULL;LPVOID remote=NULL;BOOL completed=FALSE;int rc=2;const char *stage="arguments";
 if(argc!=4)goto done;
 DWORD pid=wcstoul(argv[1],NULL,10);unsigned long long expected=wcstoull(argv[2],NULL,16);
 if(!pid||!expected||_wcsicmp(base(argv[3]),L"late_probe.dll")||wcslen(argv[3])>=MAX_PATH||GetFileAttributesW(argv[3])==INVALID_FILE_ATTRIBUTES)goto done;
 stage="open";p=OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ|PROCESS_VM_WRITE|PROCESS_VM_OPERATION|PROCESS_CREATE_THREAD,FALSE,pid);if(!p)goto done;
 FILETIME c,e,k,u;WCHAR path[MAX_PATH];DWORD len=MAX_PATH;
 stage="identity";
 if(!GetProcessTimes(p,&c,&e,&k,&u)||((((unsigned long long)c.dwHighDateTime<<32)|c.dwLowDateTime)!=expected)||!QueryFullProcessImageNameW(p,0,path,&len))goto done;
 if(_wcsicmp(base(path),L"steep.exe")&&_wcsicmp(base(path),L"late_fixture.exe"))goto done;
 MODULEENTRY32W existing;
 if(module(pid,L"late_probe.dll",&existing)){stage="already_loaded";goto done;}
 stage="loader_identity";
 FARPROC loader=GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"LoadLibraryW");HMODULE owner=NULL;
 if(!loader||!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCWSTR)(uintptr_t)loader,&owner))goto done;
 if(!GetModuleFileNameW(owner,path,MAX_PATH))goto done;
 MODULEENTRY32W target;if(!module(pid,base(path),&target))goto done;
 uintptr_t offset=(uintptr_t)loader-(uintptr_t)owner;if(offset+16>target.modBaseSize)goto done;
 uintptr_t entry=(uintptr_t)target.modBaseAddr+offset;
 BYTE bytes[16];SIZE_T read=0;
 if(!ReadProcessMemory(p,(LPCVOID)entry,bytes,sizeof(bytes),&read)||read!=sizeof(bytes))goto done;
 for(int i=0;i<16;i++)if(bytes[i]!=((BYTE*)(uintptr_t)loader)[i])goto done;
 stage="path_allocation";SIZE_T size=(wcslen(argv[3])+1)*sizeof(WCHAR),wrote=0;
 remote=VirtualAllocEx(p,NULL,size,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(!remote)goto done;
 if(!WriteProcessMemory(p,remote,argv[3],size,&wrote)||wrote!=size)goto done;
 stage="load_thread";t=CreateRemoteThread(p,NULL,0,(LPTHREAD_START_ROUTINE)entry,remote,0,NULL);if(!t)goto done;
 stage="wait";DWORD wait=WaitForSingleObject(t,5000);if(wait!=WAIT_OBJECT_0)goto done;completed=TRUE;
 stage="module_verification";if(!module(pid,L"late_probe.dll",&existing)||_wcsicmp(existing.szExePath,argv[3]))goto done;
 printf("{\"ok\":true,\"pid\":%lu,\"module\":\"0x%llx\",\"loader\":\"0x%llx\"}\n",pid,(unsigned long long)(uintptr_t)existing.modBaseAddr,(unsigned long long)entry);rc=0;
done:
 if(rc)printf("{\"ok\":false,\"stage\":\"%s\",\"winerror\":%lu,\"thread_completed\":%s}\n",stage,GetLastError(),completed?"true":"false");
 // A timed-out thread may still need its path buffer. Never free that buffer or terminate the thread.
 if(remote&&(!t||completed))VirtualFreeEx(p,remote,0,MEM_RELEASE);
 if(t)CloseHandle(t);
 if(p)CloseHandle(p);
 return rc;
}
