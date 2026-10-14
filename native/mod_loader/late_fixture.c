#include <windows.h>
#include <stdio.h>
int main(void){FILETIME c,e,k,u;GetProcessTimes(GetCurrentProcess(),&c,&e,&k,&u);printf("{\"pid\":%lu,\"created\":\"%llx\"}\n",GetCurrentProcessId(),((unsigned long long)c.dwHighDateTime<<32)|c.dwLowDateTime);fflush(stdout);Sleep(30000);return 0;}
