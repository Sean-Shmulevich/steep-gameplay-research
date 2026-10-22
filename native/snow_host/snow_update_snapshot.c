#include "snow_update_snapshot.h"
#include <string.h>
#define LIMIT UINT64_C(0x800000000000)
static int pointer(uint64_t a) { return a>=0x10000 && a<LIMIT-0x2000; }
static int read_at(SnowUpdateMemoryRead read,void *ctx,uint64_t a,void *v,size_t n) {
    return a>=0x10000 && a<LIMIT && n<=LIMIT-a && read(ctx,a,v,n);
}
typedef struct { uint64_t table,self,entity,world,runtime,main,rider; uint32_t request,substep; } Links;
static int links(SnowUpdateMemoryRead read,void *ctx,const SnowUpdateBinding *b,Links *l) {
#define Q(addr,field) do { if(!read_at(read,ctx,(addr),&(field),sizeof(field))) return 0; } while(0)
    memset(l,0,sizeof *l);
    if(!pointer(b->actor) || !pointer(b->actor_table) || !pointer(b->world)) return 0;
    Q(b->actor,l->table); Q(b->actor+0x1050,l->self); Q(b->actor+0x10,l->entity);
    if(l->table!=b->actor_table || l->self!=b->actor || !pointer(l->entity)) return 0;
    Q(l->entity+0x60,l->world); Q(b->actor+0x168,l->runtime);
    if(l->world!=b->world || !pointer(l->runtime)) return 0;
    Q(l->runtime+0x6e8,l->main); Q(l->runtime+0xb90,l->rider);
    if(!pointer(l->main) || (l->rider && !pointer(l->rider))) return 0;
    if(b->request_counter) { Q(b->request_counter,l->request); }
    if(b->substep_counter) { Q(b->substep_counter,l->substep); }
    return 1;
#undef Q
}
int snow_update_snapshot(SnowUpdateMemoryRead read,void *ctx,const SnowUpdateBinding *b,SnowUpdateSnapshot *out) {
    Links a,z; SnowUpdateSnapshot s={0};
    if(!out) return 0;
    memset(out,0,sizeof *out);
    if(!read || !b || !links(read,ctx,b,&a)) return 0;
#define R(addr,dst,n) do { if(!read_at(read,ctx,(addr),(dst),(n))) return 0; } while(0)
    const uint32_t offsets[4]={0x1fa,0xfdc,0xfc8,0xfc9};
    for(unsigned i=0;i<4;i++) R(b->actor+offsets[i],&s.gates[i],1);
    R(a.runtime+0x1570,s.pending,sizeof s.pending);
    R(a.runtime+0xa80,&s.preconsume_counter,sizeof s.preconsume_counter);
    R(a.runtime+0x1580,s.preconsume_timers,sizeof s.preconsume_timers);
    uint64_t bodies[2]={a.main,a.rider};
    for(unsigned i=0;i<2;i++) if(bodies[i]) {
        R(bodies[i]+0x1a0,s.linear[i],sizeof s.linear[i]);
        R(bodies[i]+0x1ac,s.angular[i],sizeof s.angular[i]);
        R(bodies[i]+0x124,&s.inverse_mass[i],sizeof s.inverse_mass[i]);
    }
    if(!links(read,ctx,b,&z) || memcmp(&a,&z,sizeof a)) return 0;
    s.runtime=a.runtime; s.main_body=a.main; s.rider_body=a.rider;
    s.request=a.request; s.substep=a.substep;
    s.valid=SNOW_SNAPSHOT_VALID | (a.rider ? SNOW_SNAPSHOT_RIDER_PRESENT : 0) |
        (b->request_counter ? SNOW_SNAPSHOT_REQUEST_VALID : 0) |
        (b->substep_counter ? SNOW_SNAPSHOT_SUBSTEP_VALID : 0);
    *out=s; return 1;
#undef R
}

int snow_update_resolve_binding(SnowUpdateMemoryRead read,void *ctx,uint64_t actor,
                               const SnowUpdateProfile *p,SnowUpdateBinding *out) {
    uint64_t addresses[12],values[12],entity,world,runtime,physics,state,target;
    unsigned n=0; uint32_t counter;
    if(!out) return 0;
    memset(out,0,sizeof *out);
    if(!read || !p || !pointer(actor) || !pointer(p->actor_table) ||
       !pointer(p->runtime_table) || !pointer(p->original_target) || !pointer(p->world_step_callback)) return 0;
#define ANCHOR(at,dst) do {     addresses[n]=(at); if(!read_at(read,ctx,(at),&values[n],8)) return 0;     (dst)=values[n++]; } while(0)
    ANCHOR(actor,target); if(target!=p->actor_table) return 0;
    ANCHOR(actor+0x1050,target); if(target!=actor) return 0;
    ANCHOR(p->actor_table+0x2c0,target); if(target!=p->original_target) return 0;
    ANCHOR(actor+0x10,entity); if(!pointer(entity)) return 0;
    ANCHOR(entity+0x60,world); if(!pointer(world)) return 0;
    ANCHOR(actor+0x168,runtime); if(!pointer(runtime)) return 0;
    ANCHOR(runtime,target); if(target!=p->runtime_table) return 0;
    ANCHOR(runtime+0x6f0,target); if(target!=actor) return 0;
    ANCHOR(world+0xff0,physics); if(!pointer(physics)) return 0;
    ANCHOR(physics+0x18,state); if(!pointer(state)) return 0;
    ANCHOR(state,target); if(target!=physics) return 0;
    ANCHOR(state+0x360,target); if(target!=p->world_step_callback) return 0;
    uint64_t job;
    if(!read_at(read,ctx,state+0x10,&job,8) || job!=state+0x1b0 ||
       !read_at(read,ctx,job+0x58,&counter,4)) return 0;
    for(unsigned i=0;i<n;i++) {
        if(!read_at(read,ctx,addresses[i],&target,8) || target!=values[i]) return 0;
    }
    if(!read_at(read,ctx,state+0x10,&target,8) || target!=job) return 0;
    SnowUpdateBinding binding={actor,p->actor_table,world,job+0x58,0};
    *out=binding; return 1;
#undef ANCHOR
}
