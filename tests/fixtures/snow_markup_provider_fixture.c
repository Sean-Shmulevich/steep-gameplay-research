#include "snow_markup_provider.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>
static unsigned char mem[0x20000];static unsigned calls,fail,mutate;
static const uint64_t base=UINT64_C(0x140000000);
static void put(uint64_t a,uint64_t v){for(unsigned i=0;i<8;i++)mem[a+i]=(unsigned char)(v>>(i*8));}
static int readmem(void *ctx,uint64_t a,void *b,size_t n){
 (void)ctx;calls++;assert(n<=17);if(calls==fail)return 0;
 if(calls==mutate)put(0x17050,77);
 if(a==base+0x2909848&&n==8){uint64_t v=base+0x12f2d20;memcpy(b,&v,8);return 1;}
 if(a>=sizeof mem||n>sizeof mem-a)return 0;
 memcpy(b,mem+a,n);return 1;
}
static void setup(unsigned mode){
 memset(mem,0,sizeof mem);calls=fail=mutate=0;
 put(0x10000,base+0x1e789b8);put(0x106c8,0x11000);put(0x11000,base+0x1e7d4b0);
 put(0x11628,0x10000);put(0x106c0,0x12000);put(0x11388,0x12000);
 put(0x12050,0x13000);put(0x12068,0x19000);mem[0x12072]=93;
 put(0x130b0,0x14000);put(0x14000,base+0x2909790);put(0x14020,0x15000);
 put(0x15080,0x16000);put(0x17a10,0x18000);
 put(0x18000,mode==1?(uint64_t)-0x1000:0x17000);
 put(0x18008,1|((uint64_t)(mode&1)<<62)|((uint64_t)((mode>>1)&1)<<61));
 put(0x17050,0xc00002);mem[0x17060]=2;
}
static int observe(SnowMarkupUpdateSnapshot *s){return snow_markup_provider_observe(readmem,NULL,0x10000,base,0x4000000,s);}
static void rejected(void){SnowMarkupUpdateSnapshot s,z;memset(&s,0xff,sizeof s);memset(&z,0,sizeof z);assert(!observe(&s));assert(!memcmp(&s,&z,sizeof s));}
int main(void){
 SnowMarkupUpdateSnapshot s;unsigned total=0;
 for(unsigned m=0;m<4;m++){setup(m);assert(observe(&s));assert(s.record_count==1&&s.notification_count==93&&s.records[0].key==0xc00002);total=calls;}
 setup(0);put(0x18008,8);assert(observe(&s)&&s.record_count==8);total=calls;
 assert(total<=56);
 for(unsigned i=1;i<=total;i++){setup(0);put(0x18008,8);fail=i;rejected();}
 setup(0);put(0x18008,8);mutate=total/2+1;rejected();
 setup(0);put(0x11628,0x19900);rejected();
 setup(0);put(0x14000,base+1);rejected();
 setup(0);put(0x18008,9);rejected();
 setup(0);put(0x14020,0);assert(observe(&s)&&s.attachment==0&&s.record_count==0);
 printf("provider sampler passed: modes, %u read failures, mutation, identity, capacity, null attachment\n",total);
}
