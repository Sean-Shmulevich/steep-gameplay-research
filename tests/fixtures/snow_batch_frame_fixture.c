#include "snow_batch_frame.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define BASE UINT64_C(0x100000)
static unsigned char mem[0x6000];
static unsigned reads,fail,change;
static uint64_t change_address;
static const uint64_t job=BASE,owner=BASE+0x3000,world=BASE+0x5000,caller=0x12345678;
static void q(uint64_t a,uint64_t x){memcpy(mem+a-BASE,&x,8);}
static void d(uint64_t a,uint32_t x){memcpy(mem+a-BASE,&x,4);}
static int reader(void *ctx,uint64_t a,void *out,size_t n){
    assert(ctx==mem);++reads;
    if(reads==change) mem[change_address-BASE]^=1;
    if(reads==fail || a<BASE || a>=BASE+sizeof mem || n>BASE+sizeof mem-a)return 0;
    memcpy(out,mem+a-BASE,n);return 1;
}
static void setup(void){
    memset(mem,0,sizeof mem);reads=fail=change=0;
    q(job+0x1b58,caller);q(job+0x1b60,owner);q(job+0x1b70,1);
    q(owner,world);d(owner+0x1390,2);d(owner+0x1394,0x3c088889);d(owner+0x136c,0x3c888889);
    q(world+0x20,UINT64_MAX);
}
static int observe(SnowBatchFrame *out){return snow_batch_frame(reader,mem,job,caller,world,0x3c088889,0x3c888889,out);}
static void reject(void){
    SnowBatchFrame out,zero={0};memset(&out,0xff,sizeof out);
    assert(!observe(&out));assert(!memcmp(&out,&zero,sizeof out));
}
int main(void){
    setup();SnowBatchFrame out;assert(observe(&out));assert(reads==16);
    assert(out.timing_owner==owner && out.world==world && out.ordinal==1 && out.selected_count==2);
    assert(out.outer_completion_counter==UINT64_MAX && out.elapsed_bits==0x3c088889 && out.consumed_bits==0x3c888889);
    setup();q(job+0x1b70,0);q(world+0x20,0);assert(observe(&out));
    assert(out.ordinal==0 && out.outer_completion_counter==0);
    for(unsigned i=1;i<=16;i++){setup();fail=i;reject();}
    uint64_t fields[]={job+0x1b58,job+0x1b60,job+0x1b70,owner,owner+0x1390,owner+0x1394,owner+0x136c,world+0x20};
    for(unsigned i=0;i<8;i++){setup();change=9;change_address=fields[i];reject();}
    setup();q(job+0x1b58,caller+1);reject();assert(reads==1);
    setup();q(job+0x1b70,2);reject();
    setup();q(job+0x1b70,UINT64_C(1)<<32);reject();
    setup();d(owner+0x1390,0);reject();
    setup();q(owner,world+8);reject();assert(reads==4);
    setup();q(job+0x1b60,UINT64_MAX-4);reject();
    setup();assert(!snow_batch_frame(reader,mem,UINT64_MAX-8,caller,world,0,0,&out));assert(reads==0);
    puts("PASS: batch frame caller/world/clock guards, every read failure, bracket changes and ordinal bounds");
}
