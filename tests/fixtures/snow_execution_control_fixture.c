#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include "snow_plugin.h"
int main(int argc,char **argv){
    assert(argc==4);HMODULE dll=LoadLibraryA(argv[1]);assert(dll);
    typedef int (*Initialize)(const SnowHostApiV1 *,SnowPluginV1 *);
    Initialize init=(Initialize)(uintptr_t)GetProcAddress(dll,"SnowMod_Initialize");assert(init);
    SnowHostApiV1 api={0};SnowPluginV1 plugin={0};
    api.struct_size=sizeof api;api.api_version=SNOW_PLUGIN_API_VERSION;api.config_path=argv[2];
    assert(init(NULL,&plugin)==1);assert(init(&api,NULL)==1);
    int result=init(&api,&plugin);assert(result==atoi(argv[3]));
    if(!result)assert(plugin.struct_size==sizeof plugin && plugin.api_version==SNOW_PLUGIN_API_VERSION);
    printf("initialize=%d\n",result);return 0;
}
