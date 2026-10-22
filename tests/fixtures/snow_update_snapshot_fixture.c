#include "snow_update_snapshot.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define BASE UINT64_C(0x100000)
static unsigned char memory[0x10000];
static unsigned reads,fail_at,change_at;
static uint64_t change_address;
static void writeq(uint64_t a,uint64_t v) { memcpy(memory+a-BASE,&v,8); }
static void writef(uint64_t a,float v) { memcpy(memory+a-BASE,&v,4); }
static int reader(void *ctx,uint64_t a,void *dst,size_t n) {
    assert(ctx==memory); reads++;
    if(reads==change_at) memory[change_address-BASE]^=8;
    if(reads==fail_at || a<BASE || a>=BASE+sizeof memory || n>BASE+sizeof memory-a) return 0;
    memcpy(dst,memory+a-BASE,n); return 1;
}
static SnowUpdateBinding binding={BASE,BASE+0x9000,BASE+0xa000,BASE+0xb000,BASE+0xb008};
static void setup(void) {
    memset(memory,0,sizeof memory); reads=fail_at=change_at=0;
    writeq(BASE,binding.actor_table); writeq(BASE+0x1050,BASE); writeq(BASE+0x10,BASE+0x2000);
    writeq(BASE+0x2060,binding.world); writeq(BASE+0x168,BASE+0x3000);
    writeq(BASE+0x36e8,BASE+0x5000); writeq(BASE+0x3b90,BASE+0x6000);
    writeq(binding.request_counter,17); writeq(binding.substep_counter,2);
    memory[0x1fa]=1; memory[0xfc8]=1; memory[0xfc9]=1;
    for(unsigned j=0;j<4;j++) writef(BASE+0x4570+4*j,(float)j+1);
    for(unsigned i=0;i<2;i++) {
        uint64_t body=BASE+0x5000+i*0x1000;
        for(unsigned j=0;j<6;j++) writef(body+0x1a0+4*j,(float)(10*i+j));
        writef(body+0x124,i ? .5f : .25f);
    }
}
static int sample(SnowUpdateSnapshot *out) { return snow_update_snapshot(reader,memory,&binding,out); }
static void invalid(SnowUpdateSnapshot *out) {
    SnowUpdateSnapshot zero={0}; memset(out,0xff,sizeof *out);
    assert(!sample(out)); assert(!memcmp(out,&zero,sizeof zero));
}
int main(void) {
    SnowUpdateSnapshot s; setup(); assert(sample(&s)); unsigned total=reads;
    assert(s.valid==3 && s.pending[3]==4 && s.runtime==BASE+0x3000);
    assert(s.linear[0][2]==2 && s.angular[0][0]==3 && s.angular[1][2]==15);
    assert(s.inverse_mass[0]==.25f && s.inverse_mass[1]==.5f);
    assert(s.request==17 && s.substep==2 && s.gates[0] && !s.gates[1]);
    for(unsigned i=1;i<=total;i++) { setup(); fail_at=i; invalid(&s); }
    /* Mutate each guarded link/counter between the two bracketing passes. */
    uint64_t guards[]={BASE,BASE+0x1050,BASE+0x10,BASE+0x2060,BASE+0x168,
                      BASE+0x36e8,BASE+0x3b90,binding.request_counter,binding.substep_counter};
    for(unsigned i=0;i<sizeof guards/sizeof *guards;i++) {
        setup(); change_at=10; change_address=guards[i]; invalid(&s);
    }
    setup(); writeq(BASE+0x3b90,0); assert(sample(&s));
    assert(s.valid==1 && !s.rider_body && s.angular[1][2]==0);
    setup(); writeq(BASE+0x168,UINT64_MAX); invalid(&s);
    setup(); writeq(BASE+0x1050,BASE+8); invalid(&s);
    setup(); writeq(BASE+0x2060,BASE+8); invalid(&s);
    setup(); writeq(BASE+0x36e8,0); invalid(&s);
    assert(!snow_update_snapshot(reader,memory,&binding,NULL));
    printf("PASS: %u read failures, 9 link/counter changes, absent rider and invalid identities\n",total);
    return 0;
}
