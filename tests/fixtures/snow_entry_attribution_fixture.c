#include "snow_entry_attribution.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define BASE UINT64_C(0x10000)
static unsigned char mem[0x4000];
static unsigned reads,fail,change;
static uint64_t change_address;
static void q(uint64_t a,uint64_t x){memcpy(mem+a-BASE,&x,8);}
static void d(uint64_t a,uint32_t x){memcpy(mem+a-BASE,&x,4);}
static int reader(void *ctx,uint64_t a,void *out,size_t n){
    assert(ctx==mem);++reads;
    if(reads==change)mem[change_address-BASE]^=1;
    if(reads==fail || a<BASE || a>=BASE+sizeof mem || n>BASE+sizeof mem-a)return 0;
    memcpy(out,mem+a-BASE,n);return 1;
}
static SnowEntryProfile p={0x1234,0x2345,0x3456,0x4567};
static SnowEntryRegisters r;
static uint64_t actor=BASE+0x3000;
static void setup(void){
    memset(mem,0,sizeof mem);reads=fail=change=0;
    r=(SnowEntryRegisters){BASE,BASE+0x2000,1,0x1234,0};
    q(BASE,p.job_table);q(BASE+0x198,BASE+0x1000);d(BASE+0x1a4,5);
    q(BASE+0x1f8,BASE+0x800);q(BASE+0x800,p.callable_table);
    q(r.range_slot,BASE+0x1020);q(actor,p.actor_table);
    q(BASE+0x1038,actor);
}
static void rejected(void){
    SnowEntryAttribution out,zero={0};memset(&out,0xff,sizeof out);
    assert(!snow_entry_attribute(reader,mem,&p,&r,actor,&out));
    assert(!memcmp(&out,&zero,sizeof out));
}
int main(void){
    SnowEntryAttribution out;setup();
    assert(snow_entry_attribute(reader,mem,&p,&r,actor,&out));
    assert(out.job==BASE && out.record==BASE+0x1030 && out.record_index==3 && out.initial_count==5);
    unsigned total=reads;assert(total==18);
    for(unsigned i=1;i<=total;i++){setup();fail=i;rejected();}
    uint64_t fields[]={BASE,BASE+0x198,BASE+0x1a4,BASE+0x1f8,BASE+0x800,
                       BASE+0x2000,actor,BASE+0x1030,BASE+0x1038};
    for(unsigned i=0;i<sizeof fields/sizeof fields[0];i++){
        setup();change=10;change_address=fields[i];rejected();
    }
    setup();r.return_address++;rejected();assert(reads==0);
    setup();r.local_index=UINT64_MAX;rejected();
    setup();q(r.range_slot,BASE+0x1001);rejected();
    setup();q(r.range_slot,BASE+0x1050);rejected();
    setup();d(BASE+0x1a4,0);rejected();
    setup();d(BASE+0x1a4,0x4000);rejected();
    setup();r.job=UINT64_MAX-7;rejected();
    setup();q(BASE+0x198,UINT64_MAX-31);q(r.range_slot,UINT64_MAX-15);r.local_index=1;rejected();
    puts("PASS: entry attribution guards, bracket changes and bounded reads");
}
