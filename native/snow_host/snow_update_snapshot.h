#ifndef SNOW_UPDATE_SNAPSHOT_H
#define SNOW_UPDATE_SNAPSHOT_H
#include "snow_update_trace.h"
/* Build-specific layout from CENTRAL_IMPULSE.md. The exact-read callback must
 * validate process/build identity and safely reject inaccessible memory.
 * Bracketing rejects changing links/counters; it does not pin lifetime or detect
 * ABA, nor make body reads atomic. All output is invalid on any failed read.
 */
typedef int (*SnowUpdateMemoryRead)(void *, uint64_t, void *, size_t);
typedef struct {
    uint64_t actor, actor_table, world, request_counter, substep_counter;
} SnowUpdateBinding;
enum { SNOW_SNAPSHOT_VALID=1, SNOW_SNAPSHOT_RIDER_PRESENT=2 };
int snow_update_snapshot(SnowUpdateMemoryRead, void *, const SnowUpdateBinding *, SnowUpdateSnapshot *);
#endif
