#include "snow_gate_inputs.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned char memory[0x20000];
static unsigned calls,fail,mutate;
static uint64_t change_at,change_value;
static const uint64_t base=UINT64_C(0x140000000);
static void put(uint64_t a,uint64_t value){for(unsigned i=0;i<8;i++)memory[a+i]=(unsigned char)(value>>(8*i));}
static void word(uint64_t a,uint32_t value){for(unsigned i=0;i<4;i++)memory[a+i]=(unsigned char)(value>>(8*i));}
static int readmem(void *c,uint64_t a,void *b,size_t n){
    (void)c;calls++;assert(n<=16);
    if(calls==fail)return 0;
    if(calls==mutate)put(change_at,change_value);
    if(a>=sizeof memory||n>sizeof memory-a)return 0;
    memcpy(b,memory+a,n);return 1;
}
static void setup(void){
    memset(memory,0,sizeof memory);calls=fail=mutate=0;
    put(0x10000,base+0x1e7a350);put(0x11050,0x10000);put(0x10168,0x12000);
    put(0x12000,base+0x2918ea8);put(0x126f0,0x10000);
    put(0x135a8,0x15000);put(0x135b0,0x16000);
    word(0x129f0,1);word(0x12a6c,2);word(0x12a70,3);word(0x12ab4,4);
    word(0x13520,5);word(0x15164,6);
    for(unsigned i=0;i<4;i++)word(0x16030+4*i,7+i);
}
static int observe(SnowGateInputs *s){return snow_gate_inputs_observe(readmem,NULL,0x10000,base,0x4000000,s);}
static void reject(void){SnowGateInputs s,z;memset(&s,255,sizeof s);memset(&z,0,sizeof z);assert(!observe(&s));assert(!memcmp(&s,&z,sizeof s));}
int main(void){
    SnowGateInputs s;setup();assert(observe(&s));assert(calls==26);
    assert(s.actor==0x10000&&s.runtime==0x12000&&s.shape==0x15000&&s.config==0x16000);
    assert(s.immersion==1&&s.alternate==2&&s.activity==3&&s.timer==4&&s.elapsed==5&&s.total_volume==6);
    assert(s.refill_divisor==7&&s.duration==8&&s.lower_other==9&&s.lower_one==10);
    for(unsigned i=1;i<=26;i++){setup();fail=i;reject();}
    const uint64_t fields[]={0x129f0,0x12a6c,0x12a70,0x12ab4,0x13520,0x15164,0x16030,0x16034,0x16038,0x1603c};
    for(unsigned i=0;i<10;i++){setup();mutate=14;change_at=fields[i];change_value=99;reject();}
    setup();put(0x126f0,0x19900);reject();
    setup();put(0x135a8,0);reject();
    setup();put(0x135b0,UINT64_C(0x7ffffffffff0));reject();
    /* Equal scalar values cannot conceal a changed shape identity. */
    setup();memcpy(memory+0x17000,memory+0x15000,0x168);
    mutate=14;change_at=0x135a8;change_value=0x17000;reject();
    setup();word(0x129f0,0x7fc12345);assert(observe(&s)&&s.immersion==0x7fc12345);
    setup();assert(!snow_gate_inputs_observe(NULL,NULL,0x10000,base,0x4000000,&s)&&calls==0);
    assert(!snow_gate_inputs_observe(readmem,NULL,0x10000,base,0x4000000,NULL));
    puts("gate-input fixture passed: 26 read failures, every scalar mutation, identity and range guards");
}
