#include "snow_command_admission.h"
#include <string.h>
_Static_assert(sizeof(uintptr_t)==8,"inspected layout requires 64-bit ABI");
SnowCommandAdmissionStatus snow_command_admit(const SnowCommandAdmission *b,
                                             const SnowCommandDescriptor *d) {
    if(!b || !d || !b->manager || !b->enter || !b->leave || !b->produce ||
       !b->check || !d->invoker || !d->context)
        return SNOW_COMMAND_INVALID_BINDING;
    /* Binding and descriptor are caller-owned immutable inputs for this call. */
    SnowCommandDescriptor copy=*d;
    SnowCommandAdmissionStatus result;
    b->enter(b->manager);
    if(!b->check(b->manager,b->check_context)) {
        result=SNOW_COMMAND_STALE_BINDING;
    } else {
        uintptr_t array;
        uint32_t fields[4]; /* count, write index, read index, capacity */
        memcpy(&array,(const unsigned char *)b->manager+0x30,sizeof array);
        memcpy(fields,(const unsigned char *)b->manager+0x38,sizeof fields);
        uint32_t count=fields[0],write=fields[1],read=fields[2],capacity=fields[3];
        if(!array || (array&7) || !capacity || capacity>INT32_MAX ||
           count>capacity || write>=capacity || read>=capacity ||
           (uintptr_t)capacity>(UINTPTR_MAX-array)/104) {
            result=SNOW_COMMAND_INVALID_RING;
        } else if(count==capacity) {
            result=SNOW_COMMAND_FULL;
        } else {
            b->produce(b->manager,&copy,0);
            result=SNOW_COMMAND_SUBMITTED;
        }
    }
    b->leave(b->manager);
    return result;
}
