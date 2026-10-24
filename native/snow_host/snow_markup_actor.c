#include "snow_markup_actor.h"
#include <string.h>
#define END UINT64_C(0x800000000000)
static int valid(uint64_t a,size_t n){return a>=0x10000 && a<END && n<=END-a;}
static uint32_t u32(const unsigned char *b){return (uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static uint64_t u64(const unsigned char *b){return u32(b)|((uint64_t)u32(b+4)<<32);}
static int rd(SnowEntryRead r,void *ctx,uint64_t a,void *b,size_t n){return valid(a,n)&&r(ctx,a,b,n)==1;}
static int ptr(SnowEntryRead r,void *ctx,uint64_t a,uint64_t *v){unsigned char b[8];if(!rd(r,ctx,a,b,8))return 0;*v=u64(b);return valid(*v,1);}
static int word(SnowEntryRead r,void *ctx,uint64_t a,uint32_t *v){unsigned char b[4];if(!rd(r,ctx,a,b,4))return 0;*v=u32(b);return 1;}
static int sample(SnowEntryRead r,void *ctx,uint64_t actor,uint64_t base,SnowMarkupActorSnapshot *s){
    unsigned char b[16];uint64_t p;memset(s,0,sizeof *s);s->actor=actor;
    if(!ptr(r,ctx,actor,&p)||p!=base+0x1e7a350)return 0;
    if(!ptr(r,ctx,actor+0x1050,&p)||p!=actor)return 0;
    if(!ptr(r,ctx,actor+0x10,&s->entity)||!valid(s->entity,0x68))return 0;
    if(!ptr(r,ctx,s->entity+0x60,&s->world)||!valid(s->world,0x1064))return 0;
    if(!word(r,ctx,s->world+0x1060,&s->world_interval_bits))return 0;
    if(!word(r,ctx,actor+0x1018,&s->current_mode))return 0;
    if(!s->current_mode){
        if(!ptr(r,ctx,actor+0x1020,&s->state_owner)||!valid(s->state_owner,0x28))return 0;
        if(!word(r,ctx,s->state_owner+0x18,&s->outer_state))return 0;
        s->outer_present=1;
        if(!s->outer_state){
            if(!ptr(r,ctx,s->state_owner+0x20,&s->state_child)||!valid(s->state_child,0x1c))return 0;
            if(!word(r,ctx,s->state_child+0x18,&s->inner_state))return 0;
            s->inner_present=1;
        }
    }
    if(!rd(r,ctx,actor+0x168,b,8))return 0;
    s->runtime=u64(b);
    if(s->runtime){
        if(!valid(s->runtime,0x1580)||!ptr(r,ctx,s->runtime,&p)||p!=base+0x2918ea8)return 0;
        if(!ptr(r,ctx,s->runtime+0x6f0,&p)||p!=actor)return 0;
        if(!rd(r,ctx,s->runtime+0x1570,b,16))return 0;
        for(unsigned i=0;i<4;i++)s->pending_bits[i]=u32(b+4*i);
        s->runtime_present=1;
    }
    if(!rd(r,ctx,actor+0x210,b,16))return 0;
    for(unsigned i=0;i<4;i++)s->normal_bits[i]=u32(b+4*i);
    if(!rd(r,ctx,actor+0x250,b,16))return 0;
    for(unsigned i=0;i<4;i++)s->current_bits[i]=u32(b+4*i);
    if(!word(r,ctx,actor+0xfcc,&s->gain_state))return 0;
    if(!rd(r,ctx,actor+0x1b4,&s->reverse_fallback,1)||!rd(r,ctx,actor+0xfc9,&s->fc9,1)||!rd(r,ctx,actor+0xfdc,&s->fdc,1))return 0;
    return 1;
}
int snow_markup_actor_observe(SnowEntryRead r,void *ctx,uint64_t actor,uint64_t base,uint64_t size,SnowMarkupActorSnapshot *out){
    SnowMarkupActorSnapshot a,b;if(!out)return 0;memset(out,0,sizeof *out);
    if(!r||!valid(actor,0x1058)||size<0x2918eb0||size>0x40000000||!valid(base,(size_t)size))return 0;
    if(!sample(r,ctx,actor,base,&a)||!sample(r,ctx,actor,base,&b)||memcmp(&a,&b,sizeof a))return 0;
    *out=a;return 1;
}
