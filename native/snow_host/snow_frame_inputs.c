#include "snow_frame_inputs.h"
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
static int image_range(uint64_t a,size_t n,uint64_t base,uint64_t size){return a>=base&&a-base<=size&&n<=size-(a-base);}
static int sample(SnowEntryRead r,void *c,uint64_t actor,uint64_t base,uint64_t size,SnowFrameInputs *s){
    uint64_t p;unsigned char mode;memset(s,0,sizeof *s);s->actor=actor;
    if(!pointer(r,c,actor,&p)||p!=base+0x1e7a350||
       !pointer(r,c,actor+0x1050,&p)||p!=actor||
       !pointer(r,c,actor+0x168,&s->runtime)||!valid(s->runtime,0x15a0)||
       !pointer(r,c,s->runtime,&p)||p!=base+0x2918ea8||
       !pointer(r,c,s->runtime+0x6f0,&p)||p!=actor||
       !pointer(r,c,actor+0x190,&s->receiver)||
       !pointer(r,c,s->receiver,&s->receiver_table)||!image_range(s->receiver_table,0x48,base,size)||
       !pointer(r,c,s->receiver_table+0x40,&s->callback)||!image_range(s->callback,1,base,size)||
       !pointer(r,c,s->runtime+0x5e8,&s->owner)||!valid(s->owner,0x240)||
       !pointer(r,c,s->runtime+0x1598,&s->config)||
       !read_bytes(r,c,s->config,&mode,1))return 0;
    s->physical_mode=mode;
    for(unsigned i=0;i<3;i++)if(!words(r,c,s->runtime+0xb40+16*i,s->cached_basis[i],4))return 0;
    for(unsigned i=0;i<4;i++)if(!words(r,c,s->owner+0x1c0+16*i,s->forward[i],4))return 0;
    for(unsigned i=0;i<4;i++)if(!words(r,c,s->owner+0x200+16*i,s->inverse[i],4))return 0;
    return words(r,c,s->runtime+0x1520,&s->elapsed,1);
}
int snow_frame_inputs_observe(SnowEntryRead r,void *c,uint64_t actor,uint64_t base,uint64_t size,SnowFrameInputs *out){
    SnowFrameInputs a,b;if(!out)return 0;memset(out,0,sizeof *out);
    if(!r||!valid(actor,0x1058)||size<0x2918eb0||size>0x40000000||!valid(base,(size_t)size))return 0;
    if(!sample(r,c,actor,base,size,&a)||!sample(r,c,actor,base,size,&b)||memcmp(&a,&b,sizeof a))return 0;
    *out=a;return 1;
}
