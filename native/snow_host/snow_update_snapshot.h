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
    /* Zero counters mean unavailable, not an observed zero. Nonzero counters
     * must be independently attributed by the acquisition adapter. */
} SnowUpdateBinding;
enum { SNOW_SNAPSHOT_VALID=1, SNOW_SNAPSHOT_RIDER_PRESENT=2,
       SNOW_SNAPSHOT_REQUEST_VALID=4, SNOW_SNAPSHOT_SUBSTEP_VALID=8 };
typedef struct {
    uint64_t actor_table, runtime_table, original_target, world_step_callback;
} SnowUpdateProfile;
/* Resolve the world job's started counter from a freshly acquired actor.
 * Does not discover actors or prove registry membership. Substep is unavailable.
 * All identity links are bracketed. Profile values require external build proof. */
int snow_update_resolve_binding(SnowUpdateMemoryRead, void *, uint64_t actor,
                               const SnowUpdateProfile *, SnowUpdateBinding *);
int snow_update_snapshot(SnowUpdateMemoryRead, void *, const SnowUpdateBinding *, SnowUpdateSnapshot *);
#endif
