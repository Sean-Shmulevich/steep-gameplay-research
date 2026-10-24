#include "snow_point_inputs.h"
#include <string.h>
#define END UINT64_C(0x800000000000)
static int valid(uint64_t a,size_t n){return a>=0x10000&&a<END&&n<=END-a;}
static uint32_t u32(const unsigned char *b){return (uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static uint64_t u64(const unsigned char *b){return u32(b)|((uint64_t)u32(b+4)<<32);}
static int rd(SnowEntryRead r,void *c,uint64_t a,void *b,size_t n){return valid(a,n)&&r(c,a,b,n)==1;}
static int qword(SnowEntryRead r,void *c,uint64_t a,uint64_t *v){unsigned char b[8];if(!rd(r,c,a,b,8))return 0;*v=u64(b);return 1;}
static int ptr(SnowEntryRead r,void *c,uint64_t a,uint64_t *v){return qword(r,c,a,v)&&valid(*v,1);}
static int words(SnowEntryRead r,void *c,uint64_t a,uint32_t *v,unsigned n){unsigned char b[16];if(!rd(r,c,a,b,4*n))return 0;for(unsigned i=0;i<n;i++)v[i]=u32(b+4*i);return 1;}
static int sample(SnowEntryRead r,void *c,uint64_t actor,uint64_t base,SnowPointInputs *s,SnowPointDiagnostic *d){
    uint64_t p;unsigned char b[2];memset(s,0,sizeof *s);s->actor=actor;d->count_valid=0;d->directional_count=d->summed_count=0;
    d->stage=10;
    if(!ptr(r,c,actor,&p)||p!=base+0x1e7a350)return 0;
    d->stage=11;
    if(!ptr(r,c,actor+0x1050,&p)||p!=actor)return 0;
    d->stage=12;
    if(!ptr(r,c,actor+0x168,&s->runtime)||!valid(s->runtime,0x1594))return 0;
    d->stage=13;
    if(!ptr(r,c,s->runtime,&p)||p!=base+0x2918ea8)return 0;
    d->stage=14;
    if(!ptr(r,c,s->runtime+0x6f0,&p)||p!=actor)return 0;
    d->stage=15;
    if(!ptr(r,c,s->runtime+0x6e8,&s->body)||!valid(s->body,0x19c))return 0;
    d->stage=16;
    if(!ptr(r,c,s->body+0x30,&s->descriptor)||!valid(s->descriptor,0x54))return 0;
    d->stage=17;
    if(!rd(r,c,s->descriptor+0x52,b,2))return 0;
    s->flags=b[0];s->kind=b[1];
    d->stage=18;
    if(!words(r,c,s->runtime+0x1520,&s->runtime_scale,1))return 0;
    d->stage=19;
    for(unsigned i=0;i<3;i++)if(!words(r,c,s->body+0x40+16*i,s->basis[i],3)||!words(r,c,s->body+0x170+16*i,s->local_inertia[i],3))return 0;
    d->stage=20;
    if(!words(r,c,s->body+0x70,s->translation,3)||!words(r,c,s->body+0x128,s->local_center,3))return 0;
    d->stage=21;
    if(!qword(r,c,s->runtime+0x6a0,&s->directional_count))return 0;
    d->directional_count=s->directional_count;d->count_valid|=1;
    if(s->directional_count>SNOW_POINT_DIRECTIONAL_LIMIT)return 0;
    d->stage=22;
    if(!qword(r,c,s->runtime+0x6a8,&s->directional_data))return 0;
    d->stage=23;
    if(!qword(r,c,s->runtime+0x6d0,&s->summed_count))return 0;
    d->summed_count=s->summed_count;d->count_valid|=2;
    if(s->summed_count>SNOW_POINT_SUMMED_LIMIT)return 0;
    d->stage=24;
    if(!qword(r,c,s->runtime+0x6d8,&s->summed_data))return 0;
    d->stage=25;
    if(s->directional_count&&!valid(s->directional_data,(size_t)s->directional_count*0x140))return 0;
    d->stage=26;
    if(s->summed_count&&!valid(s->summed_data,(size_t)s->summed_count*0x50))return 0;
    d->stage=27;
    for(unsigned i=0;i<s->directional_count;i++){
        uint64_t a=s->directional_data+i*0x140;SnowDirectionalInput *v=&s->directional[i];
        if(!words(r,c,a+0x80,v->point,4)||!words(r,c,a+0x90,v->direction,4)||!rd(r,c,a+0xa4,&v->enabled,1))return 0;
    }
    d->stage=28;
    for(unsigned i=0;i<s->summed_count;i++){
        uint64_t a=s->summed_data+i*0x50;SnowSummedInput *v=&s->summed[i];
        if(!words(r,c,a+0x10,v->a,4)||!words(r,c,a+0x20,v->b,4)||!words(r,c,a+0x30,v->point,4)||!rd(r,c,a+0x48,b,2))return 0;
        v->kind=b[0];v->enabled=b[1];
    }
    return 1;
}
typedef struct {SnowEntryRead read;void *context;SnowPointDiagnostic *diagnostic;} CountedRead;
static int counted(void *context,uint64_t at,void *dst,size_t n){
    CountedRead *c=context;c->diagnostic->reads++;
    int ok=c->read(c->context,at,dst,n);if(ok!=1)c->diagnostic->read_failed=1;return ok;
}
int snow_point_inputs_observe_detailed(SnowEntryRead r,void *c,uint64_t actor,uint64_t base,uint64_t size,SnowPointInputs *out,SnowPointDiagnostic *diagnostic){
    SnowPointInputs a,b;SnowPointDiagnostic local;SnowPointDiagnostic *d=diagnostic?diagnostic:&local;
    memset(d,0,sizeof *d);d->stage=1;if(!out)return 0;memset(out,0,sizeof *out);
    if(!r||!valid(actor,0x1058)||size<0x2918eb0||size>0x40000000||!valid(base,(size_t)size))return 0;
    CountedRead reader={r,c,d};d->pass=1;
    if(!sample(counted,&reader,actor,base,&a,d))return 0;
    d->pass=2;if(!sample(counted,&reader,actor,base,&b,d))return 0;
    d->stage=30;if(memcmp(&a,&b,sizeof a))return 0;
    *out=a;d->stage=0;return 1;
}
int snow_point_inputs_observe(SnowEntryRead r,void *c,uint64_t actor,uint64_t base,uint64_t size,SnowPointInputs *out){
    return snow_point_inputs_observe_detailed(r,c,actor,base,size,out,NULL);
}
