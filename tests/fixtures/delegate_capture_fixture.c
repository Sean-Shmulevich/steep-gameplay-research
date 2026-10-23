#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "snow_plugin.h"
int main(int argc,char **argv) {
    assert(argc==4);HMODULE dll=LoadLibraryA(argv[1]);assert(dll);
    SnowModInitializeFn init=(void *)GetProcAddress(dll,"SnowMod_Initialize");assert(init);
    SnowHostApiV1 api={0};SnowPluginV1 plugin={0};
    api.struct_size=sizeof api;api.api_version=SNOW_PLUGIN_API_VERSION;api.config_path=argv[2];
    int result=init(&api,&plugin);
    if(strcmp(argv[3],"trigger")) { assert(result==1);puts("initialize refused");return 0; }
    assert(result==0);
    char path[MAX_PATH];snprintf(path,sizeof path,"%s.trigger",argv[2]);
    FILE *f=fopen(path,"w");assert(f);fputs("synthetic trigger\n",f);fclose(f);
    snprintf(path,sizeof path,"%s.trace.jsonl",argv[2]);
    ULONGLONG end=GetTickCount64()+5000;
    char line[1024]={0};
    while(GetTickCount64()<end) {
        f=fopen(path,"r");
        if(f) { char *ok=fgets(line,sizeof line,f);fclose(f);if(ok)break; }
        Sleep(10);
    }
    assert(strstr(line,"\"compatible\":0") && strstr(line,"\"installed\":0"));
    plugin.on_unload(plugin.user);puts("incompatible executable refused");return 0;
}
