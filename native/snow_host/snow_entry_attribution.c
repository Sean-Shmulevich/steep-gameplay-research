#include "snow_entry_attribution.h"
#include <string.h>
typedef struct {
    uint64_t table, base, callable, callable_table, range, actor_table, record_actor;
    uint32_t count, tag;
} Observed;
static int read_at(SnowEntryRead read,void *ctx,uint64_t base,uint64_t offset,void *out,size_t n) {
    if(!base || offset>UINT64_MAX-base || n>UINT64_MAX-(base+offset)) return 0;
    return read(ctx,base+offset,out,n);
}
static int observe(SnowEntryRead read,void *ctx,const SnowEntryRegisters *r,
                   uint64_t actor,Observed *s,uint64_t *record) {
    memset(s,0,sizeof *s);
    if(!read_at(read,ctx,r->job,0,&s->table,8) ||
       !read_at(read,ctx,r->job,0x198,&s->base,8) ||
       !read_at(read,ctx,r->job,0x1a4,&s->count,4) ||
       !read_at(read,ctx,r->job,0x1f8,&s->callable,8) ||
       !read_at(read,ctx,s->callable,0,&s->callable_table,8) ||
       !read_at(read,ctx,r->range_slot,0,&s->range,8) ||
       !read_at(read,ctx,actor,0,&s->actor_table,8)) return 0;
    if(!s->base || !s->count || s->count>0x3fff || s->range<s->base ||
       (s->range-s->base)%16 || r->local_index>=s->count) return 0;
    uint64_t first=(s->range-s->base)/16;
    if(first>=s->count || r->local_index>=s->count-first) return 0;
    uint64_t offset=16*(first+r->local_index);
    if(offset>UINT64_MAX-s->base) return 0;
    *record=s->base+offset;
    return read_at(read,ctx,*record,0,&s->tag,4) &&
           read_at(read,ctx,*record,8,&s->record_actor,8);
}
int snow_entry_attribute(SnowEntryRead read,void *ctx,const SnowEntryProfile *p,
                         const SnowEntryRegisters *r,uint64_t actor,
                         SnowEntryAttribution *out) {
    Observed a,b; uint64_t record,again;
    if(!out) return 0;
    memset(out,0,sizeof *out);
    if(!read || !p || !r || !actor || !p->return_address || !p->job_table ||
       !p->callable_table || !p->actor_table || r->return_address!=p->return_address ||
       !observe(read,ctx,r,actor,&a,&record) || a.table!=p->job_table ||
       a.callable_table!=p->callable_table || a.actor_table!=p->actor_table ||
       a.tag!=0 || a.record_actor!=actor ||
       !observe(read,ctx,r,actor,&b,&again) || record!=again || memcmp(&a,&b,sizeof a)) return 0;
    out->job=r->job;out->callable=a.callable;out->record_base=a.base;
    out->record=record;out->actor=actor;
    out->record_index=(uint32_t)((record-a.base)/16);out->initial_count=a.count;
    return 1;
}
