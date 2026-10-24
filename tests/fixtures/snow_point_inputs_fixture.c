#include "snow_point_inputs.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned char memory[0x40000];
static unsigned calls,fail,mutate;
static const uint64_t base=UINT64_C(0x140000000);
static void put(uint64_t a,uint64_t value){for(unsigned i=0;i<8;i++)memory[a+i]=(unsigned char)(value>>(8*i));}
static int readmem(void *c,uint64_t a,void *b,size_t n){
    (void)c;calls++;assert(n<=16);
    if(calls==fail)return 0;
    if(calls==mutate)put(0x13520,0x3f000000);
    if(a>=sizeof memory||n>sizeof memory-a)return 0;
    memcpy(b,memory+a,n);return 1;
}
static void setup(void){
    memset(memory,0,sizeof memory);calls=fail=mutate=0;
    put(0x10000,base+0x1e7a350);put(0x11050,0x10000);put(0x10168,0x12000);
    put(0x12000,base+0x2918ea8);put(0x126f0,0x10000);put(0x126e8,0x15000);
    put(0x15030,0x16000);memory[0x16053]=2;
    put(0x126a0,32);put(0x126a8,0x20000);put(0x126d0,32);put(0x126d8,0x24000);
    put(0x13520,0x3f800000);put(0x15040,0x3f800000);put(0x15170,0x40000000);
    for(unsigned i=0;i<32;i++){
        put(0x20090+i*0x140,0x3f800000);memory[0x200a4+i*0x140]=1;
        put(0x24010+i*0x50,0x40000000);memory[0x24048+i*0x50]=1;memory[0x24049+i*0x50]=1;
    }
}
static int observe(SnowPointInputs *s){return snow_point_inputs_observe(readmem,NULL,0x10000,base,0x4000000,s);}
static void reject(void){SnowPointInputs s,z;memset(&s,255,sizeof s);memset(&z,0,sizeof z);assert(!observe(&s));assert(!memcmp(&s,&z,sizeof s));}
int main(void){
    SnowPointInputs s;setup();assert(observe(&s));unsigned total=calls;assert(total<=512);
    assert(s.directional_count==32&&s.summed_count==32&&s.kind==2);
    assert(s.basis[0][0]==0x3f800000&&s.local_inertia[0][0]==0x40000000);
    assert(s.directional[31].direction[0]==0x3f800000&&s.summed[31].a[0]==0x40000000);
    for(unsigned i=1;i<=total;i++){setup();fail=i;reject();}
    setup();mutate=total/2+1;reject();
    setup();put(0x126a0,33);reject();setup();put(0x126d0,33);reject();
    setup();put(0x126f0,0x19900);reject();setup();put(0x126a8,0);reject();
    setup();put(0x126d8,UINT64_C(0x7ffffffffff0));reject();
    setup();put(0x126a0,0);put(0x126a8,0);put(0x126d0,0);put(0x126d8,0);assert(observe(&s)&&!s.directional_count&&!s.summed_count);
    printf("point-input fixture passed: %u read failures; changed scale, overflow, identity and empty arrays\n",total);
}
