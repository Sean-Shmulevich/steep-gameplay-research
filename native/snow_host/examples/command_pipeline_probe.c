/* Standalone synthetic dispatcher around the real authored admission/trace code.
 * No game image, native hooks, original allocator or engine lock implementation.
 */
#include "snow_command_admission.h"
#include "snow_command_attachment.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static _Alignas(8) unsigned char manager[256], ring[2][104], holder[16];
static int depth, binding_valid=1;
static unsigned copied, cleaned;
static unsigned finalized[4], synthetic_invocations[4];
static void finalize(SnowCommandAttachment *a,void *context){
    assert(a->references==0);++*(unsigned *)context;
    /* Observation storage remains retained separately through all cached calls.
     * This callback deliberately does not free it or claim unload permission. */
}
static SnowCommandAttachment *attachment(void *record){
    SnowCommandAttachment *a;memcpy(&a,(unsigned char *)record+96,sizeof a);return a;
}
static uint64_t tick, current_thread=1;
static uint64_t clock_tick(void){return ++tick;}
static uint64_t thread_id(void){return current_thread;}
static void enter(void *p){assert(p==manager && depth==0);depth=1;}
static void leave(void *p){assert(p==manager && depth==1);depth=0;}
static int check(void *p,void *context){assert(p==manager && context==&binding_valid && depth==1);return binding_valid;}
static void *copy_record(void *dst,const void *src){
    assert(depth==1);++copied;memcpy(dst,src,104);
    SnowCommandAttachment *a=attachment(dst);
    if(a)__atomic_fetch_add(&a->references,1,__ATOMIC_SEQ_CST);
    return dst;
}
static void cleanup(void *record){
    uint32_t kind;memcpy(&kind,record,4);assert(depth==0 && kind==3);++cleaned;
    /* Synthetic service follows the inspected attachment prefix only;
     * original holder retirement and concurrent acquisition are not simulated. */
    SnowCommandAttachment *a=attachment(record);void *zero=0;
    memcpy((unsigned char *)record+96,&zero,8);
    if(a && __atomic_fetch_sub(&a->references,1,__ATOMIC_SEQ_CST)==1)
        a->vtable->destroy(a);
}
static uint32_t word(size_t offset){uint32_t v;memcpy(&v,manager+offset,4);return v;}
static void setword(size_t offset,uint32_t v){memcpy(manager+offset,&v,4);}
static void take(unsigned char *record){
    assert(word(0x38)>0);uint32_t index=word(0x40);
    memcpy(record,ring[index],104);
    memset(ring[index],0,104); /* Authored move: transfer the slot's one ref. */
    setword(0x40,(index+1)%2);setword(0x38,word(0x38)-1);
}
static uintptr_t dispatch(unsigned char *record){
    SnowCommandDescriptor *d=(SnowCommandDescriptor *)(void *)(record+24);
    uint64_t id=((SnowCommandObservation *)(void *)(d->context&~(uintptr_t)3))->request_id;
    assert(id>=101 && id<=104);++synthetic_invocations[id-101];
    return ((SnowDelegateOriginal)d->invoker)(d,(void *)(d->context&~(uintptr_t)3));
}
static uintptr_t phase_dispatch(void *storage,void *receiver){
    (void)receiver;return dispatch(storage);
}
static void print_interval(const SnowDelegateRecord *r){
    printf("{\"result\":%llu,\"thread\":%llu,\"entry_tick\":%llu,\"exit_tick\":%llu}",
        (unsigned long long)r->result,(unsigned long long)r->thread,
        (unsigned long long)r->entry_tick,(unsigned long long)r->exit_tick);
}
int main(void){
    SnowDelegateTrace phase_trace;SnowDelegateRecord phase_records[4];
    assert(snow_delegate_trace_init(&phase_trace,phase_records,4,phase_dispatch,clock_tick,thread_id));
    SnowCommandAttachment attachments[4];
    SnowCommandObservation owners[4];SnowCommandDescriptor descriptors[4];
    SnowDelegateRecord records[4][2],observed;
    SnowCommandAdmissionStatus status[4];
    uintptr_t address=(uintptr_t)ring;memcpy(manager+0x30,&address,8);setword(0x44,2);
    SnowCommandAdmission binding={manager,enter,leave,copy_record,cleanup,holder,check,&binding_valid};
    for(unsigned i=0;i<4;i++){
        assert(snow_command_observation_init(&owners[i],&descriptors[i],101+i,records[i],2,clock_tick,thread_id));
        if(i==3)binding_valid=0;
        assert(snow_command_attachment_init(&attachments[i],&finalized[i],finalize));
        status[i]=snow_command_admit_attached(&binding,&descriptors[i],&attachments[i]);
        assert(attachments[i].references==1 && finalized[i]==0);
        if(status[i]!=SNOW_COMMAND_SUBMITTED){
            assert(snow_command_attachment_release(&attachments[i]));
            assert(finalized[i]==1);
        }
    }
    assert(status[0]==SNOW_COMMAND_SUBMITTED && status[1]==SNOW_COMMAND_SUBMITTED);
    assert(status[2]==SNOW_COMMAND_FULL && status[3]==SNOW_COMMAND_STALE_BINDING);
    assert(copied==2 && cleaned==2 && word(0x54)==2);
    memset(descriptors,0,sizeof descriptors); /* Queue owns descriptor copies. */
    _Alignas(8) unsigned char cached[104],discarded[104];
    take(cached);take(discarded);cleanup(discarded); /* Discard without invocation. */
    assert(finalized[0]==0 && finalized[1]==1);
    for(unsigned i=0;i<3;i++){
        current_thread=1+i%2;
        assert(snow_delegate_trace_call(&phase_trace,cached,NULL)==101);
    }
    for(unsigned i=0;i<4;i++){
        snow_delegate_trace_close(&owners[i].trace);
        assert(snow_delegate_trace_drained(&owners[i].trace));
    }
    assert(snow_delegate_trace_call(&phase_trace,cached,NULL)==101);
    /* Closed command recorder still forwards; enclosing phase remains recorded. */
    snow_delegate_trace_close(&phase_trace);
    assert(snow_delegate_trace_drained(&phase_trace));
    assert(finalized[0]==0);
    cleanup(cached);
    for(unsigned i=0;i<4;i++)assert(finalized[i]==1 && attachments[i].references==0);
    printf("{\"evidence\":\"synthetic dispatcher with compiled admission and observer\","
           "\"game_launched\":false,\"native_phase_proved\":false,\"native_lifetime_proved\":false,\"requests\":[");
    for(unsigned i=0;i<4;i++){
        size_t count=0;
        while(snow_delegate_trace_read(&owners[i].trace,count,&observed,sizeof observed)){
            assert(observed.result==101+i && observed.entry_tick<observed.exit_tick);++count;
        }
        assert(count==(i==0?2u:0u));
        const char *admission=status[i]==SNOW_COMMAND_SUBMITTED?"submitted":status[i]==SNOW_COMMAND_FULL?"full":"stale_binding";
        printf("%s{\"id\":%u,\"admission\":\"%s\",\"observed_deliveries\":%zu,\"recorder_dropped\":%zu,\"ownership_finalized\":%u,\"synthetic_invocations\":%u,\"ownership_release_path\":\"%s\"}",
               i?",":"",101+i,admission,count,(size_t)atomic_load(&owners[i].trace.dropped),finalized[i],synthetic_invocations[i],
               i<2?"queue_cleanup":"caller_after_refusal");
    }
    assert(atomic_load(&owners[0].trace.dropped)==1);
    printf("],\"queue_remaining\":%u,\"synthetic_disposals_without_invocation\":1,"
           "\"cached_call_after_close_returned\":true,\"unload_safety_proved\":false,\"command_records\":[",word(0x38));
    for(size_t i=0;i<2;i++){
        assert(snow_delegate_trace_read(&owners[0].trace,i,&observed,sizeof observed));
        if(i)printf(",");
        print_interval(&observed);
    }
    printf("],\"phase_records\":[");
    for(size_t i=0;i<4;i++){
        assert(snow_delegate_trace_read(&phase_trace,i,&observed,sizeof observed));
        if(i)printf(",");
        print_interval(&observed);
    }
    printf("]}\n");
    return 0;
}
