#include <windows.h>
#include <stdio.h>
int main(int argc,char **argv){if(argc!=2)return 2;HMODULE m=LoadLibraryExA(argv[1],0,LOAD_WITH_ALTERED_SEARCH_PATH);printf("load=%p error=%lu\n",m,GetLastError());if(!m)return 3;for(int i=1;i<=103;i++){if(i>8&&i<100)continue;FARPROC p=GetProcAddress(m,(LPCSTR)(uintptr_t)i);printf("ordinal=%d present=%d error=%lu\n",i,p!=0,GetLastError());if(!p)return 4;}return 0;}
