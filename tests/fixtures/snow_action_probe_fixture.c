#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "snow_action_probe.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static __attribute__((section(".actionvt"),aligned(4096))) unsigned char table[4096]={1};
static unsigned calls;
static void original(void *p) {++*(unsigned *)p;++calls;}
static int sample(void *context,void *action,SnowActionSample *out) {
    assert(context==&calls);out->vector_bits[0]=*(unsigned *)action;out->active=1;return 1;
}
static void competitor(void *p) {(void)p;}
static void write_slot(void *value) {
    DWORD old,ignored;assert(VirtualProtect(table,4096,PAGE_READWRITE,&old));
    memcpy(table,&value,8);assert(VirtualProtect(table,4096,old,&ignored));
}
static SnowActionOriginal read_slot(void) {SnowActionOriginal p;memcpy(&p,table,8);return p;}
int main(int argc,char **argv) {
    assert(argc==2 || argc==3);HMODULE dll=LoadLibraryA(argv[1]);assert(dll);
    int (*configure)(uint64_t,SnowActionOriginal)=(void *)GetProcAddress(dll,"SnowActionProbe_Configure");
    int (*observed)(uint64_t,SnowActionOriginal,SnowActionRead,void *)=(void *)GetProcAddress(dll,"SnowActionProbe_ConfigureObserved");
    int (*install)(void)=(void *)GetProcAddress(dll,"SnowActionProbe_InstallSlot");
    int (*restore)(void)=(void *)GetProcAddress(dll,"SnowActionProbe_RestoreSlot");
    int (*close_trace)(size_t *,size_t *)=(void *)GetProcAddress(dll,"SnowActionProbe_Close");
    int (*read_record)(size_t,void *,size_t)=(void *)GetProcAddress(dll,"SnowActionProbe_ReadRecordSized");
    uint32_t (*abi)(void)=(void *)GetProcAddress(dll,"SnowActionProbe_ABIVersion");
    size_t (*size)(void)=(void *)GetProcAddress(dll,"SnowActionProbe_RecordSize");
    uint64_t (*frequency)(void)=(void *)GetProcAddress(dll,"SnowActionProbe_ClockFrequency");
    SnowActionOriginal dispatch=(void *)GetProcAddress(dll,"SnowActionProbe_Dispatch");
    assert(observed && configure && install && restore && close_trace && read_record && abi && size && frequency && dispatch);
    assert(abi()==2 && size()==sizeof(SnowActionRecord) && frequency()>0);
    write_slot((void *)original);DWORD old;assert(VirtualProtect(table,4096,PAGE_READONLY,&old));
    assert(observed((uintptr_t)table,original,sample,&calls));assert(!configure((uintptr_t)table,original));
    assert(install()==1 && read_slot()==dispatch);assert(!install());
    unsigned value=0;read_slot()(&value);assert(value==1 && calls==1);
    SnowActionRecord row;assert(!read_record(0,&row,sizeof row));
    if(argc==3) {
        write_slot((void *)competitor);assert(restore()==0 && read_slot()==competitor);
        write_slot((void *)dispatch);
    }
    assert(restore()==1 && read_slot()==original);
    MEMORY_BASIC_INFORMATION info;assert(VirtualQuery(table,&info,sizeof info));assert(info.Protect==PAGE_READONLY);
    size_t used=0,dropped=0;assert(close_trace(&used,&dropped) && used==1 && dropped==0);
    assert(read_record(0,&row,sizeof row));assert(row.action==(uintptr_t)&value && row.exit_tick>=row.entry_tick);
    assert(row.sample_attempted && row.before_valid && row.after_valid);
    assert(row.before.vector_bits[0]==0 && row.after.vector_bits[0]==1 && row.after.active==1);
    assert(!read_record(0,&row,sizeof row-1));
    dispatch(&value);assert(value==2 && calls==2);assert(close_trace(&used,&dropped) && used==1);
    assert(restore()==1);puts("PASS: guarded action slot, restoration, capture and late forwarding");
}
