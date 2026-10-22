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
    Q(b->request_counter,l->request); Q(b->substep_counter,l->substep);
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
    uint64_t bodies[2]={a.main,a.rider};
    for(unsigned i=0;i<2;i++) if(bodies[i]) {
        R(bodies[i]+0x1a0,s.linear[i],sizeof s.linear[i]);
        R(bodies[i]+0x1ac,s.angular[i],sizeof s.angular[i]);
        R(bodies[i]+0x124,&s.inverse_mass[i],sizeof s.inverse_mass[i]);
    }
    if(!links(read,ctx,b,&z) || memcmp(&a,&z,sizeof a)) return 0;
    s.runtime=a.runtime; s.main_body=a.main; s.rider_body=a.rider;
    s.request=a.request; s.substep=a.substep;
    s.valid=SNOW_SNAPSHOT_VALID | (a.rider ? SNOW_SNAPSHOT_RIDER_PRESENT : 0);
    *out=s; return 1;
#undef R
}
