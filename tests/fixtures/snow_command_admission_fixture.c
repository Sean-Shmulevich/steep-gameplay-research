#include "snow_command_admission.h"
#include <assert.h>
#include <string.h>
static _Alignas(8) unsigned char manager[256],array[208];
static int depth,checks,produced,valid=1;
static void enter(void *m){assert(m==manager);++depth;}
static void leave(void *m){assert(m==manager && depth>0);--depth;}
static int check(void *m,void *c){assert(m==manager && c==&valid && depth==1);++checks;return valid;}
static void produce(void *m,const SnowCommandDescriptor *d,uint8_t alternate){
    assert(depth==1 && d->context==4 && !alternate);enter(m);assert(depth==2);
    uint32_t count;memcpy(&count,manager+0x38,4);++count;memcpy(manager+0x38,&count,4);
    ++produced;leave(m);
}
static void setup(uint32_t count,uint32_t capacity){
    memset(manager,0,sizeof manager);uintptr_t a=(uintptr_t)array;
    memcpy(manager+0x30,&a,8);memcpy(manager+0x38,&count,4);memcpy(manager+0x44,&capacity,4);
}
int main(void){
    SnowCommandAdmission b={manager,enter,leave,produce,check,&valid};
    SnowCommandDescriptor d={1,0,4,1};
    setup(0,1);assert(snow_command_admit(&b,&d)==SNOW_COMMAND_SUBMITTED);
    assert(depth==0 && produced==1);
    assert(snow_command_admit(&b,&d)==SNOW_COMMAND_FULL);assert(depth==0 && produced==1);
    valid=0;assert(snow_command_admit(&b,&d)==SNOW_COMMAND_STALE_BINDING);assert(depth==0);
    valid=1;setup(2,1);assert(snow_command_admit(&b,&d)==SNOW_COMMAND_INVALID_RING);
    setup(0,0);assert(snow_command_admit(&b,&d)==SNOW_COMMAND_INVALID_RING);
    setup(0,1);uint32_t index=1;memcpy(manager+0x40,&index,4);
    assert(snow_command_admit(&b,&d)==SNOW_COMMAND_INVALID_RING);
    b.check=0;int before=checks;assert(snow_command_admit(&b,&d)==SNOW_COMMAND_INVALID_BINDING);
    assert(checks==before && depth==0 && produced==1);return 0;
}
