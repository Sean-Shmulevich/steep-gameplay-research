#include "snow_markup_provider.h"
#include <string.h>
#define END UINT64_C(0x800000000000)
static int valid(uint64_t a,size_t n){return a>=0x10000 && a<END && n<=END-a;}
static uint32_t u32(const unsigned char *b){return (uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static uint64_t u64(const unsigned char *b){return u32(b)|((uint64_t)u32(b+4)<<32);}
static int rd(SnowEntryRead r,void *ctx,uint64_t a,void *b,size_t n){return valid(a,n)&&r(ctx,a,b,n)==1;}
static int ptr(SnowEntryRead r,void *ctx,uint64_t a,uint64_t *v){unsigned char b[8];if(!rd(r,ctx,a,b,8))return 0;*v=u64(b);return valid(*v,1);}
static int sample(SnowEntryRead r,void *ctx,uint64_t c,uint64_t base,SnowMarkupUpdateSnapshot *s){
    unsigned char b[17];uint64_t p;memset(s,0,sizeof *s);s->component=c;
    if(!ptr(r,ctx,c,&p)||p!=base+0x1e789b8)return 0;
    if(!ptr(r,ctx,c+0x6c8,&s->controller)||!valid(s->controller,0x630))return 0;
    if(!ptr(r,ctx,s->controller,&p)||p!=base+0x1e7d4b0)return 0;
    if(!ptr(r,ctx,s->controller+0x628,&p)||p!=c)return 0;
    if(!ptr(r,ctx,c+0x6c0,&s->markup)||!valid(s->markup,0x78))return 0;
    if(!ptr(r,ctx,s->controller+0x388,&p)||p!=s->markup)return 0;
    if(!rd(r,ctx,s->markup+0x68,b,12))return 0;
    s->notification_data=u64(b);s->notification_count=(uint32_t)b[10]|(uint32_t)b[11]<<8;
    if(!ptr(r,ctx,s->markup+0x50,&s->query_owner)||!valid(s->query_owner,0xb8))return 0;
    if(!ptr(r,ctx,s->query_owner+0xb0,&s->interface)||!valid(s->interface,0x28))return 0;
    if(!ptr(r,ctx,s->interface,&p)||p!=base+0x2909790)return 0;
    if(!ptr(r,ctx,p+0xb8,&p)||p!=base+0x12f2d20)return 0;
    if(!rd(r,ctx,s->interface+0x20,b,8))return 0;
    s->attachment=u64(b);if(!s->attachment)return 1;
    if(!valid(s->attachment,0x88)||!ptr(r,ctx,s->attachment+0x80,&s->graph)||!valid(s->graph,0x1a18))return 0;
    if(!ptr(r,ctx,s->graph+0x1a10,&s->header)||!rd(r,ctx,s->header,b,16))return 0;
    s->data=u64(b);s->packed_header=u64(b+8);s->record_count=(uint32_t)s->packed_header&0x1fffffff;
    if(s->record_count>SNOW_MARKUP_RECORD_LIMIT)return 0;
    if((s->packed_header&(UINT64_C(1)<<62))&&!(s->packed_header&(UINT64_C(1)<<61)))s->data+=s->header;
    if(s->record_count&&!valid(s->data,s->record_count*0x68))return 0;
    for(uint32_t i=0;i<s->record_count;i++){
        if(!rd(r,ctx,s->data+i*0x68+0x50,b,17))return 0;
        s->records[i].key=u32(b);s->records[i].scalar54_bits=u32(b+4);
        s->records[i].start_bits=u32(b+8);s->records[i].end_bits=u32(b+12);s->records[i].flags=b[16];
    }
    return 1;
}
int snow_markup_provider_observe(SnowEntryRead r,void *ctx,uint64_t component,uint64_t base,uint64_t size,SnowMarkupUpdateSnapshot *out){
    SnowMarkupUpdateSnapshot a,b;if(!out)return 0;memset(out,0,sizeof *out);
    if(!r||!valid(component,0x6d0)||size<0x2909850||size>0x40000000||!valid(base,(size_t)size))return 0;
    if(!sample(r,ctx,component,base,&a)||!sample(r,ctx,component,base,&b)||memcmp(&a,&b,sizeof a))return 0;
    *out=a;return 1;
}
