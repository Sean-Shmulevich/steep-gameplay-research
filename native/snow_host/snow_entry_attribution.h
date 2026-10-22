#ifndef SNOW_ENTRY_ATTRIBUTION_H
#define SNOW_ENTRY_ATTRIBUTION_H
#include <stddef.h>
#include "snow_entry_thunk.h"
typedef int (*SnowEntryRead)(void *,uint64_t,void *,size_t);
typedef struct {
    uint64_t return_address, job_table, callable_table, actor_table;
} SnowEntryProfile;
typedef struct {
    uint64_t job, callable, record_base, record, actor;
    uint32_t record_index, initial_count;
} SnowEntryAttribution;
/* Inspected build layout only. Caller proves build/profile and supplies a bounded
 * exact reader that rejects inaccessible memory. Entry registers must be copied
 * before the original actor prologue. Zero output on failure. Bracketing rejects
 * changed observations, but does not pin lifetime, detect ABA or identify a batch
 * generation. No writes, forwarding, installation or TLS access. */
int snow_entry_attribute(SnowEntryRead,void *,const SnowEntryProfile *,
                         const SnowEntryRegisters *,uint64_t actor,
                         SnowEntryAttribution *);
#endif
