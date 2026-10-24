#include "snow_markup_actor.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>
static unsigned char mem[0x30000];static unsigned calls,fail,mutate;
static const uint64_t base=UINT64_C(0x140000000);
static void put(uint64_t a,uint64_t v){for(unsigned i=0;i<8;i++)mem[a+i]=(unsigned char)(v>>(i*8));}
static int readmem(void *ctx,uint64_t a,void *b,size_t n){
 (void)ctx;calls++;assert(n<=16);if(calls==fail)return 0;
 if(calls==mutate)put(0x19570,77);
 if(a>=sizeof mem||n>sizeof mem-a)return 0;
 memcpy(b,mem+a,n);return 1;
}
static void setup(void){
 memset(mem,0,sizeof mem);calls=fail=mutate=0;
 put(0x10000,base+0x1e7a350);put(0x11050,0x10000);put(0x10010,0x12000);
 put(0x12060,0x13000);put(0x14060,0x3c888889);put(0x11020,0x15000);
 put(0x16020,0x17000);put(0x17010,0x1a000);put(0x16010,0x1a000);
 put(0x1a040,0x10000);put(0x1a050,0x1b000);put(0x1b000,0x1c000);put(0x1b00c,0x80000000);
 put(0x1a720,0x3f800000);put(0x1c0e0,0x40000000);
 put(0x15020,0x16000);put(0x16018,5);put(0x10168,0x18000);
 put(0x18000,base+0x2918ea8);put(0x186f0,0x10000);put(0x19570,0x3f800000);
 put(0x10218,0x3f800000);mem[0x10fc9]=1;mem[0x10fdc]=1;
}
static int observe(SnowMarkupActorSnapshot *s){return snow_markup_actor_observe(readmem,NULL,0x10000,base,0x4000000,s);}
static void rejected(void){SnowMarkupActorSnapshot s,z;memset(&s,0xff,sizeof s);memset(&z,0,sizeof z);assert(!observe(&s));assert(!memcmp(&s,&z,sizeof s));}
int main(void){
 SnowMarkupActorSnapshot s;setup();assert(observe(&s));unsigned total=calls;assert(total<=72);
 assert(s.outer_present&&s.inner_present&&s.inner_state==5&&s.pending_bits[0]==0x3f800000&&s.runtime_present&&s.fc9&&s.fdc);
 assert(s.projection_inputs_present&&s.direction_bits[0]==0x3f800000&&s.projection_gain_bits==0x40000000);
 setup();put(0x15018,1);assert(observe(&s)&&s.vector_receiver==0x16000&&s.projection_inputs_present);
 for(unsigned i=1;i<=total;i++){setup();fail=i;rejected();}
 setup();mutate=total/2+1;rejected();
 setup();put(0x1b00c,0);rejected();setup();put(0x1a040,0x19900);rejected();
 setup();put(0x186f0,0x19900);rejected();setup();put(0x11050,0x19900);rejected();
 setup();put(0x11018,1);put(0x11020,0);assert(observe(&s)&&!s.outer_present&&!s.inner_present);
 setup();put(0x15018,3);put(0x15020,0);assert(observe(&s)&&s.outer_present&&!s.inner_present);
 setup();put(0x10168,0);assert(observe(&s)&&!s.runtime_present);
 printf("actor sampler passed: %u read failures, changed pending, identity, mode skips, null runtime\n",total);
}
