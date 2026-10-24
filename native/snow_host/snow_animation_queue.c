#include "snow_animation_queue.h"
#include <string.h>
#define USER_END UINT64_C(0x800000000000)
static uint16_t u16(const unsigned char *p) {return (uint16_t)(p[0]|(uint16_t)p[1]<<8);}
static uint32_t u32(const unsigned char *p) {return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t u64(const unsigned char *p) {return u32(p)|((uint64_t)u32(p+4)<<32);}
static int address(uint64_t a,size_t n) {return a>=0x10000 && a<USER_END && n<=USER_END-a;}
static int read_at(SnowEntryRead r,void *ctx,uint64_t a,void *b,size_t n) {
    return address(a,n) && r(ctx,a,b,n)==1;
}
static int in_image(uint64_t a,size_t n,uint64_t base,uint64_t size) {
    return a>=base && a-base<size && n<=size-(a-base);
}
static int sample(SnowEntryRead r,void *ctx,uint64_t component,uint64_t owner,
                  uint64_t base,uint64_t size,SnowAnimationQueueSnapshot *s) {
    unsigned char b[64];uint64_t vectors[3][SNOW_ANIMATION_QUEUE_LIMIT];
    const size_t offsets[3]={0xf0,0x180,0x210};
    memset(s,0,sizeof *s);s->component=component;s->owner=owner;
    if(!read_at(r,ctx,component,b,8)||u64(b)!=base+0x1f289d0 ||
       !read_at(r,ctx,component+16,b,8)||u64(b)!=owner)return 0;
    for(size_t k=0;k<3;k++) {
        if(!read_at(r,ctx,component+offsets[k],b,12))return 0;
        s->arrays[k]=u64(b);s->headers[k]=u16(b+8);s->counts[k]=u16(b+10);
        if(s->counts[k]>SNOW_ANIMATION_QUEUE_LIMIT || s->counts[k]>(s->headers[k]&0x3fff))return 0;
    }
    size_t n=s->counts[0];
    if(n!=s->counts[1] || n!=s->counts[2])return 0;
    if(!n)return 1;
    for(size_t k=0;k<3;k++) {
        if(!read_at(r,ctx,s->arrays[k],b,n*8))return 0;
        for(size_t i=0;i<n;i++)vectors[k][i]=u64(b+8*i);
    }
    for(size_t i=0;i<n;i++) {
        SnowAnimationQueueRow *row=&s->rows[i];row->event=vectors[0][i];
        /* Keep array identities even for null events, without dereferencing. */
        row->handles[0]=vectors[1][i];row->handles[1]=vectors[2][i];
        if(!row->event)continue;
        if(!read_at(r,ctx,row->event,b,8))return 0;
        row->table=u64(b);row->table_in_image=(uint8_t)in_image(row->table,0x58,base,size);
        if(row->table_in_image) {
            if(!read_at(r,ctx,row->table+0x50,b,8))return 0;
            row->handler=u64(b);row->handler_in_image=(uint8_t)in_image(row->handler,1,base,size);
        }
        for(size_t k=0;k<2;k++) {
            uint64_t h=row->handles[k];
            if(!address(h,16)||!read_at(r,ctx,h,b,8))return 0;
            row->payloads[k]=u64(b);
            if(!read_at(r,ctx,h+12,b,4))return 0;
            row->status[k]=u32(b);
        }
    }
    return 1;
}
int snow_animation_queue_observe(SnowEntryRead r,void *ctx,uint64_t component,
    uint64_t owner,uint64_t base,uint64_t size,SnowAnimationQueueSnapshot *out) {
    SnowAnimationQueueSnapshot a,b;
    if(!out)return 0;
    memset(out,0,sizeof *out);
    if(!r || !address(component,0x21c) || !address(owner,1) || size<0x1f28a00 ||
       size>0x40000000 || !address(base,(size_t)size))return 0;
    if(!sample(r,ctx,component,owner,base,size,&a) ||
       !sample(r,ctx,component,owner,base,size,&b) || memcmp(&a,&b,sizeof a))return 0;
    *out=a;return 1;
}
