#define WIN32_LEAN_AND_MEAN
#include <windows.h>

static HMODULE self;
static void log_line(const char *text, DWORD length) {
    WCHAR path[MAX_PATH]; DWORD n=GetModuleFileNameW(self,path,MAX_PATH);
    if (!n || n>=MAX_PATH) return;
    while (n && path[n-1]!=L'\\') --n;
    const WCHAR name[]=L"snow_mod_loader.log";
    if(n+sizeof(name)/sizeof(WCHAR)>MAX_PATH) return;
    for(DWORD j=0;j<sizeof(name)/sizeof(WCHAR);j++) path[n+j]=name[j];
    HANDLE f=CreateFileW(path,FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    if(f!=INVALID_HANDLE_VALUE){DWORD written;WriteFile(f,text,length,&written,NULL);CloseHandle(f);}
}
BOOL WINAPI LoaderEntry(HINSTANCE instance,DWORD reason,LPVOID reserved) {
    (void)reserved;
    if(reason==DLL_PROCESS_ATTACH){
        self=instance;
        DisableThreadLibraryCalls(instance);
        const char message[]="snow loader v0: proxy attached; forwarding only\r\n";
        log_line(message,sizeof(message)-1);
    }
    return TRUE;
}
