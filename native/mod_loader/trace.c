#include "proxy.c"

__declspec(dllimport) DWORD WINAPI XInputSetState(DWORD user, void *vibration);
static LONG count;
DWORD WINAPI TraceSetState(DWORD user, void *vibration) {
    DWORD saved=GetLastError();
    LONG n=InterlockedIncrement(&count);
    if(n<=16){const char s[]="SetState enter\r\n";log_line(s,sizeof(s)-1);}
    SetLastError(saved);
    DWORD result=XInputSetState(user,vibration);
    saved=GetLastError();
    if(n<=16){const char s[]="SetState returned\r\n";log_line(s,sizeof(s)-1);}
    SetLastError(saved);
    return result;
}
