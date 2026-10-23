#ifndef SNOW_COMMAND_ADMISSION_H
#define SNOW_COMMAND_ADMISSION_H
#include "snow_command_observation.h"
/* Authored guard for the recovered ordinary kind-3 producer layout.
 * Caller MUST retain manager/lock/array throughout this call and descriptor
 * context/module through every possible delivery. Equality checks cannot pin
 * lifetime. Build, routines and recursive-lock identity must be verified first.
 * All callbacks return normally; no SEH, longjmp or C++ exception recovery.
 * No installer, allocator, scheduler hold, module pin or unload permission.
 */
typedef void (*SnowCommandLock)(void *wrapper);
typedef void (*SnowCommandProducer)(void *manager,const SnowCommandDescriptor *,uint8_t alternate);
/* Called under queue lock, bounded/nonblocking, must not submit or acquire other
 * engine locks. This detects a changed binding; it does not establish lifetime. */
typedef int (*SnowCommandBindingCheck)(void *manager,void *context);
typedef struct {
    void *manager;
    SnowCommandLock enter,leave;
    SnowCommandProducer produce;
    SnowCommandBindingCheck check;
    void *check_context;
} SnowCommandAdmission;
typedef enum {
    SNOW_COMMAND_SUBMITTED=1, SNOW_COMMAND_FULL=2,
    SNOW_COMMAND_INVALID_BINDING=3, SNOW_COMMAND_STALE_BINDING=4,
    SNOW_COMMAND_INVALID_RING=5
} SnowCommandAdmissionStatus;
/* SUBMITTED means the guarded native producer returned. No exactly-once,
 * execution, completion, counter consistency or gameplay-mutation guarantee.
 * The gate does not repair full submissions made by other native producers.
 */
SnowCommandAdmissionStatus snow_command_admit(const SnowCommandAdmission *,
                                             const SnowCommandDescriptor *);
#endif
