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
    binding.request_counter=BASE+0xb000; binding.substep_counter=BASE+0xb008;
    memset(memory,0,sizeof memory); reads=fail_at=change_at=0;
    writeq(BASE,binding.actor_table); writeq(BASE+0x1050,BASE); writeq(BASE+0x10,BASE+0x2000);
    writeq(BASE+0x2060,binding.world); writeq(BASE+0x168,BASE+0x3000);
    writeq(BASE+0x36e8,BASE+0x5000); writeq(BASE+0x3b90,BASE+0x6000);
    writeq(binding.request_counter,17); writeq(binding.substep_counter,2);
    memory[0x1fa]=1; memory[0xfc8]=1; memory[0xfc9]=1;
    int32_t counter=INT32_MIN; memcpy(memory+0x3a80,&counter,4);
    writef(BASE+0x4580,-.25f); writef(BASE+0x4584,.75f);
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
    assert(s.valid==15 && s.pending[3]==4 && s.runtime==BASE+0x3000);
    assert(s.linear[0][2]==2 && s.angular[0][0]==3 && s.angular[1][2]==15);
    assert(s.preconsume_counter==INT32_MIN && s.preconsume_timers[0]==-.25f && s.preconsume_timers[1]==.75f);
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
    assert(s.valid==13 && !s.rider_body && s.angular[1][2]==0);
    setup(); writeq(BASE+0x168,UINT64_MAX); invalid(&s);
    setup(); writeq(BASE+0x1050,BASE+8); invalid(&s);
    setup(); writeq(BASE+0x2060,BASE+8); invalid(&s);
    setup(); writeq(BASE+0x36e8,0); invalid(&s);
    setup(); binding.substep_counter=0; assert(sample(&s));
    assert(s.valid==7 && s.request==17 && s.substep==0);
    binding.request_counter=0; assert(sample(&s));
    assert(s.valid==3 && s.request==0 && s.substep==0);
    binding.substep_counter=BASE+0xb008; assert(sample(&s));
    assert(s.valid==11 && s.request==0 && s.substep==2);
    assert(!snow_update_snapshot(reader,memory,&binding,NULL));
    /* Fresh actor -> owning physics state -> world-job started counter. */
    SnowUpdateProfile profile={BASE+0x9000,BASE+0x9100,BASE+0xe000,BASE+0xe100};
    SnowUpdateBinding resolved,zero={0}; unsigned resolver_reads=0;
    for(unsigned failure=0;failure<=27;failure++) {
        setup(); writeq(BASE+0x92c0,profile.original_target);
        writeq(BASE+0x3000,profile.runtime_table); writeq(BASE+0x36f0,BASE);
        writeq(BASE+0xaff0,BASE+0xc000); writeq(BASE+0xc018,BASE+0xd000);
        writeq(BASE+0xd000,BASE+0xc000); writeq(BASE+0xd010,BASE+0xd1b0);
        writeq(BASE+0xd360,profile.world_step_callback); writeq(BASE+0xd208,19);
        fail_at=failure;
        int ok=snow_update_resolve_binding(reader,memory,BASE,&profile,&resolved);
        if(!failure) {
            assert(ok); resolver_reads=reads; assert(resolver_reads==27);
            assert(resolved.actor==BASE && resolved.world==BASE+0xa000);
            assert(resolved.request_counter==BASE+0xd208 && resolved.substep_counter==0);
        } else { assert(!ok); assert(!memcmp(&resolved,&zero,sizeof zero)); }
    }
    setup();

    printf("PASS: %u read failures, 9 link/counter changes, absent rider and invalid identities\n",total);
    return 0;
}
