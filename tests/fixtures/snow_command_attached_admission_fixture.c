#include "snow_command_admission.h"
#include <assert.h>
#include <string.h>
typedef struct { void *table; uint32_t refs; } Attachment;
static _Alignas(8) unsigned char manager[256],array[104],holder[16];
static int depth,valid=1,consume_on_leave,copies,cleanups,destroyed;
static void *attachment_of(void *r){void *a;memcpy(&a,(char *)r+96,8);return a;}
static void cleanup(void *r){
    Attachment *a=attachment_of(r);void *zero=0;
    memcpy((char *)r+96,&zero,8);++cleanups;
    if(a){assert(a->refs>0);if(--a->refs==0)++destroyed;}
}
static void enter(void *m){assert(m==manager);++depth;}
static void leave(void *m){
    assert(m==manager && depth==1);--depth;
    if(consume_on_leave && copies){
        /* Controlled consumer cleanup before producer's temporary cleanup. */
        cleanup(array);uint32_t zero=0;memcpy(manager+0x38,&zero,4);
    }
}
static int check(void *m,void *c){(void)c;assert(m==manager && depth==1);return valid;}
static void *copy(void *d,const void *s){
    assert(depth==1);memcpy(d,s,104);Attachment *a=attachment_of(d);
    if(a)++a->refs;
    ++copies;return d;
}
static void setup(void){
    memset(manager,0,sizeof manager);memset(array,0,sizeof array);
    uintptr_t storage=(uintptr_t)array;uint32_t cap=1;
    memcpy(manager+0x30,&storage,8);memcpy(manager+0x44,&cap,4);
    depth=0;valid=1;consume_on_leave=0;copies=cleanups=destroyed=0;
}
int main(void){
    SnowCommandAdmission b={manager,enter,leave,copy,cleanup,holder,check,0};
    SnowCommandDescriptor d={1,0,4,1};Attachment a={0,1};
    setup();assert(snow_command_admit_attached(&b,&d,&a)==SNOW_COMMAND_SUBMITTED);
    assert(a.refs==1 && copies==1 && cleanups==1 && destroyed==0);
    Attachment rejected={0,1};
    assert(snow_command_admit_attached(&b,&d,&rejected)==SNOW_COMMAND_FULL);
    assert(rejected.refs==1 && copies==1 && cleanups==1);
    cleanup(array);assert(a.refs==0 && destroyed==1);
    setup();a.refs=1;consume_on_leave=1;
    assert(snow_command_admit_attached(&b,&d,&a)==SNOW_COMMAND_SUBMITTED);
    assert(a.refs==0 && copies==1 && cleanups==2 && destroyed==1 && depth==0);
    setup();a.refs=1;valid=0;
    assert(snow_command_admit_attached(&b,&d,&a)==SNOW_COMMAND_STALE_BINDING);
    assert(a.refs==1 && copies==0 && cleanups==0);
    setup();uint32_t bad=2;memcpy(manager+0x38,&bad,4);
    assert(snow_command_admit_attached(&b,&d,&a)==SNOW_COMMAND_INVALID_RING);
    assert(a.refs==1 && copies==0 && cleanups==0);
    assert(snow_command_admit_attached(&b,&d,0)==SNOW_COMMAND_INVALID_BINDING);
    assert(snow_command_admit_attached(0,&d,&a)==SNOW_COMMAND_INVALID_BINDING);
    assert(a.refs==1 && copies==0 && cleanups==0);
    return 0;
}
