#include "snow_frame_inputs.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned char memory[0x20000],table[0x80];
static unsigned calls,fail,mutate;
static uint64_t change_at,change_value;
static const uint64_t base=UINT64_C(0x140000000);
static unsigned char *address(uint64_t a,size_t n){
    if(a>=base+0x1000&&a-base-0x1000<=sizeof table&&n<=sizeof table-(a-base-0x1000))return table+(a-base-0x1000);
    if(a<sizeof memory&&n<=sizeof memory-a)return memory+a;
    return NULL;
}
static void put(uint64_t a,uint64_t value){unsigned char *p=address(a,8);assert(p);for(unsigned i=0;i<8;i++)p[i]=(unsigned char)(value>>(8*i));}
static void word(uint64_t a,uint32_t value){unsigned char *p=address(a,4);assert(p);for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(value>>(8*i));}
static int readmem(void *c,uint64_t a,void *b,size_t n){
    (void)c;calls++;assert(n<=16);
    if(calls==fail)return 0;
    if(calls==mutate)put(change_at,change_value);
    unsigned char *p=address(a,n);if(!p)return 0;
    memcpy(b,p,n);return 1;
}
static void setup(void){
    memset(memory,0,sizeof memory);memset(table,0,sizeof table);calls=fail=mutate=0;
    put(0x10000,base+0x1e7a350);put(0x11050,0x10000);put(0x10168,0x12000);
    put(0x12000,base+0x2918ea8);put(0x126f0,0x10000);
    put(0x10190,0x15000);put(0x15000,base+0x1000);put(base+0x1040,base+0x2000);
    put(0x125e8,0x16000);put(0x13598,0x17000);memory[0x17000]=1;word(0x13520,55);
    for(unsigned i=0;i<12;i++)word(0x12b40+4*i,100+i);
    for(unsigned i=0;i<16;i++){word(0x161c0+4*i,200+i);word(0x16200+4*i,300+i);}
}
static int observe(SnowFrameInputs *s){return snow_frame_inputs_observe(readmem,NULL,0x10000,base,0x4000000,s);}
static void reject(void){SnowFrameInputs s,z;memset(&s,255,sizeof s);memset(&z,0,sizeof z);assert(!observe(&s));assert(!memcmp(&s,&z,sizeof s));}
int main(void){
    SnowFrameInputs s;setup();assert(observe(&s));assert(calls==46);
    assert(s.receiver==0x15000&&s.receiver_table==base+0x1000&&s.callback==base+0x2000);
    assert(s.owner==0x16000&&s.config==0x17000&&s.physical_mode==1&&s.elapsed==55);
    assert(s.cached_basis[2][3]==111&&s.forward[3][3]==215&&s.inverse[3][3]==315);
    for(unsigned i=1;i<=46;i++){setup();fail=i;reject();}
    for(unsigned group=0;group<3;group++)for(unsigned i=0;i<(group?16:12);i++){
        setup();mutate=24;change_at=(group==0?0x12b40:group==1?0x161c0:0x16200)+4*i;change_value=999;reject();
    }
    const uint64_t identity[]={0x10190,0x15000,base+0x1040,0x125e8,0x13598,0x17000,0x13520};
    for(unsigned i=0;i<7;i++){setup();mutate=24;change_at=identity[i];change_value=0;reject();}
    /* Equal payloads do not hide owner replacement. */
    setup();memcpy(memory+0x18000,memory+0x16000,0x240);
    mutate=24;change_at=0x125e8;change_value=0x18000;reject();
    setup();put(base+0x1040,base+0x4000000);reject();
    setup();put(0x15000,0x16000);reject();
    setup();put(0x125e8,UINT64_C(0x7ffffffffff0));reject();
    setup();word(0x12b40,0x7fc12345);assert(observe(&s)&&s.cached_basis[0][0]==0x7fc12345);
    setup();assert(!snow_frame_inputs_observe(NULL,NULL,0x10000,base,0x4000000,&s)&&calls==0);
    assert(!snow_frame_inputs_observe(readmem,NULL,0x10000,base,0x4000000,NULL));
    puts("frame-input fixture passed: 46 read failures, all matrix lanes, identities and bounds");
}
