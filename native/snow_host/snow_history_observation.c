#include "snow_history_observation.h"
#include <string.h>
typedef struct { SnowEntryRead read;void *context;uint32_t calls,bytes; } Reader;
typedef struct {
    uint64_t table,callback,owner,config,receiver,selected,clock;
    unsigned char owner_header[12],settings[20],reference[16],threshold_header[12],threshold[4];
} Identity;
static uint32_t u32(const unsigned char *b) {
    return (uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;
}
static uint64_t u64(const unsigned char *b) {return u32(b)|((uint64_t)u32(b+4)<<32);}
static int get(Reader *r,uint64_t base,uint64_t off,void *out,size_t size) {
    if(!base || off>UINT64_MAX-base || size>UINT64_MAX-(base+off) ||
       r->calls>=32 || size>1024-r->bytes) return 0;
    r->calls++;r->bytes+=(uint32_t)size;
    return r->read(r->context,base+off,out,size)==1;
}
static int ptr(Reader *r,uint64_t base,uint64_t off,uint64_t *out) {
    unsigned char b[8];if(!get(r,base,off,b,8))return 0;*out=u64(b);return 1;
}
static int sample(Reader *r,const SnowHistoryProfile *p,SnowHistoryActionObservation *s,Identity *g) {
    unsigned char raw[0xd0],b[24];uint64_t threshold;size_t i;
    memset(s,0,sizeof *s);memset(g,0,sizeof *g);
    if(!get(r,p->action,0,raw,sizeof raw) || u64(raw)!=p->table ||
       !ptr(r,p->table,16,&g->callback) || g->callback!=p->callback) return 0;
    g->table=p->table;g->owner=u64(raw+16);g->config=u64(raw+0xb0);
    if(!get(r,g->config,0x28,g->settings,20))return 0;
    s->channel=u32(g->settings);if(s->channel>1)return 0;
    if(!get(r,g->owner,0,g->owner_header,12) || !get(r,g->owner,0x790,g->reference,16))return 0;
    uint64_t offset=0x10+(uint64_t)s->channel*0x3c0;
    if(g->owner>UINT64_MAX-offset)return 0;
    s->history=g->owner+offset;
    if(!get(r,s->history,0x3a0,g->threshold_header,12))return 0;
    threshold=u64(g->threshold_header);
    if(!(g->threshold_header[10]|g->threshold_header[11]) || !get(r,threshold,0,g->threshold,4))return 0;
    if(!get(r,s->history,0,b,24))return 0;
    for(i=0;i<3;i++)s->history_times[i]=u64(b+i*8);
    if(!get(r,s->history,0x1a0,b,16))return 0;
    for(i=0;i<4;i++)s->history_b_bits[i]=u32(b+i*4);
    if(!get(r,s->history,0x240,b,16))return 0;
    for(i=0;i<4;i++)s->history_c_bits[i]=u32(b+i*4);
    if(!get(r,s->history,0x2e0,b,4))return 0;
    s->history_magnitude_bits=u32(b);
    if(!ptr(r,p->receiver_slot,0,&g->receiver))return 0;
    if(g->receiver && !ptr(r,g->receiver,0x188,&g->selected))return 0;
    if(g->selected) {
        if(g->selected>UINT64_MAX-0x1048)return 0;
        g->clock=g->selected+0x1048;
    } else if(!ptr(r,p->fallback_clock_slot,0,&g->clock))return 0;
    if(!ptr(r,g->clock,8,&s->clock_ticks))return 0;
    s->action=p->action;s->owner=g->owner;s->configuration=g->config;
    s->receiver=g->receiver;s->selected=g->selected;s->clock_record=g->clock;
    s->direction_kind=u32(g->settings+4);s->mode=u32(g->settings+8);
    s->hold_delay_bits=u32(g->settings+12);s->repeat_delay_bits=u32(g->settings+16);
    for(i=0;i<4;i++)s->reference_bits[i]=u32(g->reference+i*4);
    s->threshold_bits=u32(g->threshold);s->action_magnitude_bits=u32(raw+0x60);
    s->active=raw[0x30];s->previous=raw[0xb8];
    s->start_time=u64(raw+0xc0);s->repeat_time=u64(raw+0xc8);return 1;
}
int snow_history_observe(SnowEntryRead read,void *ctx,const SnowHistoryProfile *p,SnowHistoryCapture *out) {
    if(!out)return 0;
    memset(out,0,sizeof *out);
    if(!read || !p || !p->action || !p->table || !p->callback || !p->receiver_slot || !p->fallback_clock_slot)return 0;
    Reader r={read,ctx,0,0};Identity a,b;
    int ok=sample(&r,p,&out->samples[0],&a) && sample(&r,p,&out->samples[1],&b);
    out->reads=r.calls;out->bytes=r.bytes;
    if(!ok){memset(out->samples,0,sizeof out->samples);return 0;}
    out->identities_match=!memcmp(&a,&b,sizeof a);
    const SnowHistoryActionObservation *x=&out->samples[0],*y=&out->samples[1];
    out->dynamic_equal=x->active==y->active && x->previous==y->previous &&
        x->action_magnitude_bits==y->action_magnitude_bits &&
        x->start_time==y->start_time && x->repeat_time==y->repeat_time &&
        x->clock_ticks==y->clock_ticks && x->history_magnitude_bits==y->history_magnitude_bits &&
        !memcmp(x->history_times,y->history_times,sizeof x->history_times) &&
        !memcmp(x->history_b_bits,y->history_b_bits,sizeof x->history_b_bits) &&
        !memcmp(x->history_c_bits,y->history_c_bits,sizeof x->history_c_bits);
    return out->identities_match?1:2;
}
