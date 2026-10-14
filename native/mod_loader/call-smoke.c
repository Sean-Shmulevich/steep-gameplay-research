#include <windows.h>
#include <stdio.h>
#include <stdint.h>
int main(int argc,char **argv){
 if(argc!=2)return 2;
 HMODULE m=LoadLibraryExA(argv[1],0,LOAD_WITH_ALTERED_SEARCH_PATH);
 if(!m){printf("load failed %lu\n",GetLastError());return 3;}
 typedef DWORD(WINAPI *SetState)(DWORD,void*);
 SetState fn=(SetState)(uintptr_t)GetProcAddress(m,(LPCSTR)(uintptr_t)3);
 if(!fn)return 4;
 WORD vibration[2]={0,0};
 DWORD result=fn(0,vibration);
 printf("SetState user=0 motors=0 result=%lu\n",result);
 return 0;
}
