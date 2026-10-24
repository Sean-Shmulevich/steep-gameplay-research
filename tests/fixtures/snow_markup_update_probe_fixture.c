#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "snow_markup_update_probe.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static __attribute__((section(".queuevt"),aligned(4096))) unsigned char table[4096]={1};
static unsigned calls,samples;
static uint32_t expected_bits;
static void original(void *p,float value) {uint32_t bits;memcpy(&bits,&value,4);assert(bits==expected_bits);++calls;++*(unsigned *)p;}
static void competitor(void *p,float value) {(void)p;(void)value;}
static int sample(void *context,void *component,SnowMarkupUpdateSnapshot *s) {
    assert(context==&samples);++samples;memset(s,0,sizeof *s);
    s->component=(uintptr_t)component;s->record_count=(uint16_t)(*(unsigned *)component==0);return 1;
}
static void write_slot(void *p) {
    DWORD old,ignored;assert(VirtualProtect(table,4096,PAGE_READWRITE,&old));memcpy(table,&p,8);
    assert(VirtualProtect(table,4096,old,&ignored));
}
static SnowMarkupUpdateOriginal read_slot(void) {SnowMarkupUpdateOriginal p;memcpy(&p,table,8);return p;}
int main(int argc,char **argv) {
    assert(argc==3);HMODULE dll=LoadLibraryA(argv[1]);assert(dll);const char *mode=argv[2];
    int (*configure)(uint64_t,SnowMarkupUpdateOriginal,void *,SnowMarkupUpdateRead,void *)=(void *)GetProcAddress(dll,"SnowMarkupUpdateProbe_Configure");
    int (*install)(void)=(void *)GetProcAddress(dll,"SnowMarkupUpdateProbe_InstallSlot");
    int (*restore)(void)=(void *)GetProcAddress(dll,"SnowMarkupUpdateProbe_RestoreSlot");
    int (*close_trace)(size_t *,size_t *)=(void *)GetProcAddress(dll,"SnowMarkupUpdateProbe_Close");
    int (*read_record)(size_t,void *,size_t)=(void *)GetProcAddress(dll,"SnowMarkupUpdateProbe_ReadRecordSized");
    uint32_t (*abi)(void)=(void *)GetProcAddress(dll,"SnowMarkupUpdateProbe_ABIVersion");
    size_t (*size)(void)=(void *)GetProcAddress(dll,"SnowMarkupUpdateProbe_RecordSize");
    uint64_t (*frequency)(void)=(void *)GetProcAddress(dll,"SnowMarkupUpdateProbe_ClockFrequency");
    SnowMarkupUpdateOriginal dispatch=(void *)GetProcAddress(dll,"SnowMarkupUpdateProbe_Dispatch");
    assert(configure && install && restore && close_trace && read_record && abi && size && frequency && dispatch);
    assert(abi()==2 && size()==sizeof(SnowMarkupUpdateRecord) && frequency()>0);
    unsigned value=0,other=0;size_t used=0,dropped=0;SnowMarkupUpdateRecord row;
    write_slot((void *)original);DWORD old;assert(VirtualProtect(table,4096,PAGE_READONLY,&old));
    void *address=table,*heap=NULL;
    if(!strcmp(mode,"heap")){heap=VirtualAlloc(NULL,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(heap);address=heap;memcpy(heap,&(SnowMarkupUpdateOriginal){original},8);}
    assert(!configure((uintptr_t)address+1,original,&value,sample,&samples));
    assert(configure((uintptr_t)address,original,&value,sample,&samples));
    assert(!configure((uintptr_t)address,original,&value,sample,&samples));
    if(!strcmp(mode,"closed"))assert(close_trace(&used,&dropped));
    if(!strcmp(mode,"changed"))write_slot((void *)competitor);
    if(heap || !strcmp(mode,"closed") || !strcmp(mode,"changed")) {
        assert(install()==0);assert(restore()==1);assert(close_trace(&used,&dropped));
        assert(used==0 && dropped==0 && samples==0);
        assert(read_slot()==(!strcmp(mode,"changed")?competitor:original));
        if(heap)assert(VirtualFree(heap,0,MEM_RELEASE));
        puts("PASS: refused installation without modifying slot");return 0;
    }
    assert(install()==1 && read_slot()==dispatch);assert(install()==0);
    expected_bits=0x80000000;float argument;memcpy(&argument,&expected_bits,4);read_slot()(&value,argument);assert(value==1);
    read_slot()(&other,argument);assert(other==1);
    assert(samples==2 && calls==2);assert(!read_record(0,&row,sizeof row));
    if(!strcmp(mode,"conflict")) {
        write_slot((void *)competitor);assert(restore()==0 && read_slot()==competitor);
        write_slot((void *)dispatch);
    }
    assert(restore()==1 && read_slot()==original);
    MEMORY_BASIC_INFORMATION info;assert(VirtualQuery(table,&info,sizeof info));assert(info.Protect==PAGE_READONLY);
    assert(close_trace(&used,&dropped) && used==1 && dropped==0);
    assert(read_record(0,&row,sizeof row) && row.component==(uintptr_t)&value);
    assert(row.argument_bits==0x80000000);
    assert(row.before_valid && row.after_valid && row.before.record_count==1 && row.after.record_count==0);
    assert(!read_record(0,&row,sizeof row-1));
    assert(FreeLibrary(dll)); /* configured DLL remains pinned */
    expected_bits=0x7fc00001;memcpy(&argument,&expected_bits,4);dispatch(&value,argument);assert(value==2);
    assert(samples==2 && calls==3 && close_trace(&used,&dropped) && used==1);
    assert(restore()==1);puts("PASS: capture, filter, restoration, pinning and cached forwarding");
    return 0;
}
