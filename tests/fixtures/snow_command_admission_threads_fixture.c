/* Authored multi-producer admission test; no native game calls or lifetime claims. */
#include "snow_command_admission.h"
#include <assert.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sched.h>
#define THREADS 4
#define ATTEMPTS 256
static _Alignas(8) unsigned char manager[256],array[64*104],holder[16];
static pthread_mutex_t queue=PTHREAD_MUTEX_INITIALIZER,start_mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t start_cond=PTHREAD_COND_INITIALIZER;
static unsigned ready;static int go;
static _Thread_local unsigned depth;
static atomic_uint cleaned;
static unsigned accepted[THREADS*ATTEMPTS],contexts[THREADS*ATTEMPTS];
static SnowCommandAdmission binding;
static void enter(void *m){assert(m==manager);assert(pthread_mutex_lock(&queue)==0);depth++;}
static void leave(void *m){assert(m==manager&&depth==1);depth--;assert(pthread_mutex_unlock(&queue)==0);}
static int check(void *m,void *ctx){assert(m==manager&&ctx==holder&&depth==1);return 1;}
static void *copy_record(void *dst,const void *src){assert(depth==1);memcpy(dst,src,104);return dst;}
static void cleanup_record(void *record){
    assert(depth==0);SnowCommandDescriptor d;memcpy(&d,(unsigned char *)record+24,sizeof d);
    assert(d.body>=1&&d.body<=THREADS*ATTEMPTS);assert(d.context==(uintptr_t)&contexts[d.body-1]);
    atomic_fetch_add(&cleaned,1);sched_yield();
}
static void unused_invoker(void){assert(0&&"admission must not dispatch");}
static void *producer(void *arg){
    unsigned thread=(unsigned)(uintptr_t)arg;
    assert(pthread_mutex_lock(&start_mutex)==0);ready++;
    assert(pthread_cond_broadcast(&start_cond)==0);
    while(!go)assert(pthread_cond_wait(&start_cond,&start_mutex)==0);
    assert(pthread_mutex_unlock(&start_mutex)==0);
    for(unsigned i=0;i<ATTEMPTS;i++){
        unsigned index=thread*ATTEMPTS+i;
        SnowCommandDescriptor d={index+1,0,(uintptr_t)&contexts[index],(uintptr_t)unused_invoker};
        SnowCommandAdmissionStatus result=snow_command_admit(&binding,&d);
        assert(result==SNOW_COMMAND_SUBMITTED||result==SNOW_COMMAND_FULL);
        accepted[index]=result==SNOW_COMMAND_SUBMITTED;
        if((i&7)==0)sched_yield();
    }
    assert(depth==0);return NULL;
}
int main(void){
    const uint32_t capacities[]={1,7,64};
    binding=(SnowCommandAdmission){manager,enter,leave,copy_record,cleanup_record,holder,check,holder};
    for(unsigned c=0;c<3;c++){
        uint32_t capacity=capacities[c],initial=capacity-1;uintptr_t storage=(uintptr_t)array;
        memset(manager,0,sizeof manager);memset(array,0,sizeof array);memset(accepted,0,sizeof accepted);
        memcpy(manager+0x30,&storage,8);memcpy(manager+0x3c,&initial,4);memcpy(manager+0x40,&initial,4);memcpy(manager+0x44,&capacity,4);
        atomic_store(&cleaned,0);ready=0;go=0;pthread_t threads[THREADS];
        for(unsigned i=0;i<THREADS;i++)assert(pthread_create(&threads[i],NULL,producer,(void *)(uintptr_t)i)==0);
        assert(pthread_mutex_lock(&start_mutex)==0);
        while(ready<THREADS)assert(pthread_cond_wait(&start_cond,&start_mutex)==0);
        go=1;assert(pthread_cond_broadcast(&start_cond)==0);assert(pthread_mutex_unlock(&start_mutex)==0);
        for(unsigned i=0;i<THREADS;i++)assert(pthread_join(threads[i],NULL)==0);
        uint32_t count,write,budget;memcpy(&count,manager+0x38,4);memcpy(&write,manager+0x3c,4);memcpy(&budget,manager+0x54,4);
        assert(count==capacity&&budget==capacity&&write==initial&&atomic_load(&cleaned)==capacity);
        unsigned seen[THREADS*ATTEMPTS]={0},total=0;
        for(unsigned i=0;i<THREADS*ATTEMPTS;i++)total+=accepted[i];assert(total==capacity);
        for(unsigned i=0;i<capacity;i++){
            uint32_t kind;SnowCommandDescriptor d;memcpy(&kind,array+i*104,4);memcpy(&d,array+i*104+24,sizeof d);
            assert(kind==3&&d.body>=1&&d.body<=THREADS*ATTEMPTS);unsigned id=(unsigned)d.body-1;
            assert(accepted[id]&&!seen[id]);seen[id]=1;assert(d.context==(uintptr_t)&contexts[id]);
        }
    }
    puts("{\"passed\":true,\"scenarios\":3,\"producers\":4,\"total_attempts\":3072,\"game_loaded\":false}");return 0;
}
