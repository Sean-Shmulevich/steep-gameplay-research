#include "snow_command_observation.h"
_Static_assert(sizeof(uintptr_t)==8,"kind-3 descriptor requires 64-bit ABI");
_Static_assert(sizeof(SnowCommandDescriptor)==32,"four-qword descriptor required");
static uintptr_t observe(void *storage,void *receiver) {
    (void)storage;
    return (uintptr_t)((SnowCommandObservation *)receiver)->request_id;
}
static __attribute__((noinline)) uintptr_t invoke(void *storage,void *receiver) {
    SnowCommandObservation *owner=receiver;
    return snow_delegate_trace_call_from(&owner->trace,storage,receiver,
        (uintptr_t)__builtin_extract_return_addr(__builtin_return_address(0)));
}
int snow_command_observation_init(SnowCommandObservation *owner,SnowCommandDescriptor *out,
    uint64_t id,SnowDelegateRecord *records,size_t capacity,
    SnowDelegateClock clock,SnowDelegateClock thread_id) {
    if(!owner || !out || !id || ((uintptr_t)owner&3))return 0;
    if(!snow_delegate_trace_init(&owner->trace,records,capacity,observe,clock,thread_id))return 0;
    owner->request_id=id;
    /* The custom invoker supplies observation; body is retained as a descriptor
     * identity, not a request to use the engine's generic body invoker. */
    *out=(SnowCommandDescriptor){(uintptr_t)&observe,0,(uintptr_t)owner,(uintptr_t)&invoke};
    return 1;
}
