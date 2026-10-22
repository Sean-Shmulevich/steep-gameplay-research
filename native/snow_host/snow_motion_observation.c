#include "snow_motion_observation.h"
#include <string.h>
static uint32_t u32(const unsigned char *p) {
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static uint64_t u64(const unsigned char *p) {return u32(p)|((uint64_t)u32(p+4)<<32);}
static int at(SnowEntryRead r,void *ctx,uint64_t base,uint64_t off,void *out,size_t n) {
    if(!base || off>UINT64_MAX-base || n>UINT64_MAX-(base+off)) return 0;
    return r(ctx,base+off,out,n);
}
static void clear_profile(SnowMotionObservation *s) {
    s->profile_handle=s->profile=0;s->profile_valid=s->smoothing_alpha_bits=0;
}
static void profile_sample(SnowEntryRead r,void *ctx,SnowMotionObservation *s) {
    unsigned char b[16];uint64_t handle,profile;
    if(!at(r,ctx,s->motion,0x50,b,8) || !(handle=u64(b)) ||
       !at(r,ctx,handle,0,b,16) || !(u32(b+12)&0x80000000u) || !(profile=u64(b)) ||
       !at(r,ctx,profile,0x64,b,4)) return;
    s->profile_handle=handle;s->profile=profile;s->smoothing_alpha_bits=u32(b);s->profile_valid=1;
}
static int sample(SnowEntryRead r,void *ctx,uint64_t actor,uint64_t table,SnowMotionObservation *s) {
    unsigned char b[56]; size_t i;
    memset(s,0,sizeof *s);
    if(!at(r,ctx,actor,0,b,8)||u64(b)!=table || actor>UINT64_MAX-0x1010) return 0;
    s->motion=actor+0x1010;
    if(!at(r,ctx,s->motion,0x40,b,8)||u64(b)!=actor ||
       !at(r,ctx,s->motion,8,b,56)) return 0;
    s->current_mode=u32(b);s->pending_mode=u32(b+4);
    s->current=u64(b+8);s->pending=u64(b+16);
    s->lock_word=u32(b+24);s->lock_owner=u32(b+28);s->lock_depth=u32(b+32);
    s->enabled=b[36];s->query_depth=u32(b+40);s->immediate=b[44];s->pending_service=b[45];
    if(!at(r,ctx,s->motion,0x160,b,32)) return 0;
    for(i=0;i<8;i++) s->ingested[i]=u32(b+4*i);
    if(!at(r,ctx,s->motion,0x360,b,48)) return 0;
    for(i=0;i<8;i++) s->current_inputs[i]=u32(b+4*i);
    s->nonzero_counts[0]=u32(b+36);s->nonzero_counts[1]=u32(b+40);
    if(!at(r,ctx,s->motion,0x47d,s->latches,3)||!at(r,ctx,s->motion,0x6e0,b,48)) return 0;
    for(i=0;i<12;i++) s->baselines[i]=u32(b+4*i);
    profile_sample(r,ctx,s);
    if(s->current_mode!=0 || !s->current) return 1;
    if(!at(r,ctx,s->current,0x18,b,24)) return 0;
    s->state_observed=1;s->state_mode=u32(b);s->state_pending_mode=u32(b+4);
    s->state_current=u64(b+8);s->state_pending=u64(b+16);
    if((s->state_mode!=0 && s->state_mode!=3 && s->state_mode!=4) || !s->state_current) return 1;
    if(!at(r,ctx,s->state_current,0x18,b,24)) return 0;
    s->child_observed=1;s->child_mode=u32(b);s->child_pending_mode=u32(b+4);
    s->child_current=u64(b+8);s->child_pending=u64(b+16);
    return 1;
}
int snow_motion_observe(SnowEntryRead r,void *ctx,uint64_t actor,uint64_t table,SnowMotionObservation *out) {
    SnowMotionObservation a,b;
    if(!out) return 0;
    memset(out,0,sizeof *out);
    if(!r || !actor || !table || (actor&15) ||
       !sample(r,ctx,actor,table,&a)||!sample(r,ctx,actor,table,&b)) return 0;
    if(!a.profile_valid || !b.profile_valid || a.profile_handle!=b.profile_handle ||
       a.profile!=b.profile || a.smoothing_alpha_bits!=b.smoothing_alpha_bits) {
        clear_profile(&a);clear_profile(&b);
    }
    if(memcmp(&a,&b,sizeof a)) return 0;
    *out=a;return 1;
}
