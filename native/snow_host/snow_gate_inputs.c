#include "snow_gate_inputs.h"
#include <string.h>
#define END UINT64_C(0x800000000000)
static int valid(uint64_t a,size_t n){return a>=0x10000&&a<END&&n<=END-a;}
static uint32_t u32(const unsigned char *b){return (uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static int read_bytes(SnowEntryRead r,void *c,uint64_t a,void *b,size_t n){return valid(a,n)&&r(c,a,b,n)==1;}
static int pointer(SnowEntryRead r,void *c,uint64_t a,uint64_t *v){
    unsigned char b[8];if(!read_bytes(r,c,a,b,8))return 0;
    *v=u32(b)|((uint64_t)u32(b+4)<<32);return valid(*v,1);
}
static int words(SnowEntryRead r,void *c,uint64_t a,uint32_t *v,unsigned n){
    unsigned char b[16];if(!read_bytes(r,c,a,b,4*n))return 0;
    for(unsigned i=0;i<n;i++)v[i]=u32(b+4*i);
    return 1;
}
static int sample(SnowEntryRead r,void *c,uint64_t actor,uint64_t base,SnowGateInputs *s){
    uint64_t p;uint32_t pair[2],config[4];memset(s,0,sizeof *s);s->actor=actor;
    if(!pointer(r,c,actor,&p)||p!=base+0x1e7a350||
       !pointer(r,c,actor+0x1050,&p)||p!=actor||
       !pointer(r,c,actor+0x168,&s->runtime)||!valid(s->runtime,0x15b8)||
       !pointer(r,c,s->runtime,&p)||p!=base+0x2918ea8||
       !pointer(r,c,s->runtime+0x6f0,&p)||p!=actor||
       !pointer(r,c,s->runtime+0x15a8,&s->shape)||!valid(s->shape,0x168)||
       !pointer(r,c,s->runtime+0x15b0,&s->config)||!valid(s->config,0x40)||
       !words(r,c,s->runtime+0x9f0,&s->immersion,1)||
       !words(r,c,s->runtime+0xa6c,pair,2)||
       !words(r,c,s->runtime+0xab4,&s->timer,1)||
       !words(r,c,s->runtime+0x1520,&s->elapsed,1)||
       !words(r,c,s->shape+0x164,&s->total_volume,1)||
       !words(r,c,s->config+0x30,config,4))return 0;
    s->alternate=pair[0];s->activity=pair[1];s->refill_divisor=config[0];
    s->duration=config[1];s->lower_other=config[2];s->lower_one=config[3];return 1;
}
int snow_gate_inputs_observe(SnowEntryRead r,void *c,uint64_t actor,uint64_t base,uint64_t size,SnowGateInputs *out){
    SnowGateInputs a,b;if(!out)return 0;memset(out,0,sizeof *out);
    if(!r||!valid(actor,0x1058)||size<0x2918eb0||size>0x40000000||!valid(base,(size_t)size))return 0;
    if(!sample(r,c,actor,base,&a)||!sample(r,c,actor,base,&b)||memcmp(&a,&b,sizeof a))return 0;
    *out=a;return 1;
}
