#include "snow_animation_queue.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define BASE UINT64_C(0x140000000)
#define COMP UINT64_C(0x100000)
#define OWNER UINT64_C(0x200000)
#define TABLE (BASE+0x1eecd58)
static unsigned char comp[0x220], arrays[3][64], event[8], handles[2][16], slot[8];
static unsigned calls,fail_call,mutate_after;
static uint64_t mutate_address;
static void put(unsigned char *p,uint64_t v,size_t n) {for(size_t i=0;i<n;i++)p[i]=(unsigned char)(v>>(8*i));}
static int copy(uint64_t at,void *out,size_t n,uint64_t base,unsigned char *src,size_t size) {
    if(at<base || at-base>size || n>size-(at-base))return 0;
    memcpy(out,src+(size_t)(at-base),n);return 1;
}
static int read_mem(void *ctx,uint64_t at,void *out,size_t n) {
    (void)ctx;calls++;assert(n<=64);
    if(calls==fail_call)return 0;
    int ok=copy(at,out,n,COMP,comp,sizeof comp) ||
        copy(at,out,n,0x300000,arrays[0],64) || copy(at,out,n,0x310000,arrays[1],64) ||
        copy(at,out,n,0x320000,arrays[2],64) || copy(at,out,n,0x400000,event,8) ||
        copy(at,out,n,0x500000,handles[0],16) || copy(at,out,n,0x510000,handles[1],16) ||
        copy(at,out,n,TABLE+0x50,slot,8);
    if(ok && calls>mutate_after && at==mutate_address)((unsigned char *)out)[0]^=1;
    return ok;
}
static void setup(unsigned count) {
    memset(comp,0,sizeof comp);memset(arrays,0,sizeof arrays);memset(handles,0,sizeof handles);
    calls=fail_call=mutate_after=0;mutate_address=0;
    put(comp,BASE+0x1f289d0,8);put(comp+16,OWNER,8);
    for(size_t k=0;k<3;k++) {
        unsigned char *h=comp+0xf0+0x90*k;
        put(h,0x300000+0x10000*k,8);put(h+8,0x8008,2);put(h+10,count,2);
        for(size_t i=0;i<8;i++)put(arrays[k]+8*i,k==0?0x400000:(k==1?0x500000:0x510000),8);
    }
    put(event,TABLE,8);put(slot,BASE+0xa45ec0,8);
    for(size_t k=0;k<2;k++){put(handles[k],OWNER,8);put(handles[k]+8,7,4);put(handles[k]+12,0x80000001,4);}
}
static int run(SnowAnimationQueueSnapshot *out) {
    return snow_animation_queue_observe(read_mem,NULL,COMP,OWNER,BASE,0x4000000,out);
}
static void zeroed(const SnowAnimationQueueSnapshot *out) {
    SnowAnimationQueueSnapshot zero;memset(&zero,0,sizeof zero);assert(!memcmp(out,&zero,sizeof zero));
}
int main(void) {
    SnowAnimationQueueSnapshot out;
    setup(8);assert(run(&out));assert(calls==112 && out.counts[0]==8);
    assert(out.rows[7].table==TABLE && out.rows[7].handler==BASE+0xa45ec0);
    assert(out.rows[7].payloads[1]==OWNER && out.rows[7].status[1]==0x80000001);
    for(unsigned i=1;i<=112;i++) {
        setup(8);fail_call=i;memset(&out,0xff,sizeof out);assert(!run(&out));zeroed(&out);
    }
    const uint64_t mutations[]={COMP,COMP+16,COMP+0xf0,0x300000,0x400000,TABLE+0x50,0x500000,0x50000c};
    for(size_t i=0;i<sizeof mutations/sizeof *mutations;i++) {
        setup(8);mutate_address=mutations[i];mutate_after=56;
        assert(!run(&out));zeroed(&out);
    }
    setup(0);assert(run(&out) && calls==10);
    setup(1);put(arrays[0],0,8);put(arrays[1],1,8);put(arrays[2],2,8);
    assert(run(&out) && calls==16 && !out.rows[0].event);
    setup(1);put(event,0xdead0000,8);assert(run(&out));assert(!out.rows[0].table_in_image);
    setup(1);put(slot,0xdead0000,8);assert(run(&out));assert(!out.rows[0].handler_in_image);
    setup(1);put(handles[0]+12,1,4);assert(run(&out));assert(out.rows[0].status[0]==1);
    setup(1);put(comp+0x21a,0,2);assert(!run(&out));zeroed(&out);
    setup(9);assert(!run(&out));zeroed(&out);
    setup(1);put(comp+0xf8,0,2);assert(!run(&out));zeroed(&out);
    setup(1);put(arrays[1],UINT64_MAX-4,8);assert(!run(&out));zeroed(&out);
    setup(1);mutate_address=0x500008;mutate_after=0;assert(run(&out)); /* excluded refcount */
    assert(!snow_animation_queue_observe(read_mem,NULL,UINT64_MAX-4,OWNER,BASE,0x4000000,&out));zeroed(&out);
    puts("queue fixture passed: 112 read failures, 8 mutation paths, bounds and null paths");
    return 0;
}
