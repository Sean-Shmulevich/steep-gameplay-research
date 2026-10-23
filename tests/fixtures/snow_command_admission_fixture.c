#include "snow_command_admission.h"
#include <assert.h>
#include <string.h>
static _Alignas(8) unsigned char manager[256],array[208];
static int depth,checks,produced,valid=1;
static void enter(void *m){assert(m==manager);++depth;}
static void leave(void *m){assert(m==manager && depth>0);--depth;}
static int check(void *m,void *c){assert(m==manager && c==&valid && depth==1);++checks;return valid;}
static unsigned char holder[16];
static void *copy_record(void *destination,const void *source){
    assert(depth==1);memcpy(destination,source,104);++produced;return destination;
}
static void cleanup_record(void *record){
    assert(depth==0);uint32_t kind;memcpy(&kind,record,4);assert(kind==3);
    uintptr_t context;memcpy(&context,(unsigned char *)record+40,8);assert(context==4);
}
static void setup(uint32_t count,uint32_t capacity){
    memset(manager,0,sizeof manager);uintptr_t a=(uintptr_t)array;
    memcpy(manager+0x30,&a,8);memcpy(manager+0x38,&count,4);memcpy(manager+0x44,&capacity,4);
}
int main(void){
    SnowCommandAdmission b={manager,enter,leave,copy_record,cleanup_record,holder,check,&valid};
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
