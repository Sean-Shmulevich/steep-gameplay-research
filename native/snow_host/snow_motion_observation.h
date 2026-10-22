#ifndef SNOW_MOTION_OBSERVATION_H
#define SNOW_MOTION_OBSERVATION_H
#include "snow_entry_attribution.h"
typedef struct {
    uint64_t motion, current, pending, state_current, state_pending;
    uint64_t child_current, child_pending;
    uint32_t current_mode, pending_mode, lock_word, lock_owner, lock_depth, query_depth;
    uint32_t state_mode, state_pending_mode, child_mode, child_pending_mode;
    uint32_t state_observed, child_observed;
    unsigned char enabled, immediate, pending_service, latches[3];
    uint64_t profile_handle, profile;
    uint32_t profile_valid, smoothing_alpha_bits;
    uint32_t ingested[8], current_inputs[8], nonzero_counts[2], baselines[12];
} SnowMotionObservation;
/* Inspected actor/motion layout only. Caller supplies verified build and actor
 * table identity, plus a bounded exact reader. At most 24 reads, no writes or
 * calls into the game. Two identical samples required; zero output on failure.
 * Follows at most two state levels, only on inspected dispatch branches.
 * Profile failure/instability clears only profile fields, preserving motion.
 * Does not prove atomicity, lifetime, input freshness or ingestion execution.
 * Lock/depth values are observations, never permission to mutate the owner.
 */
int snow_motion_observe(SnowEntryRead,void *,uint64_t actor,uint64_t actor_table,
                        SnowMotionObservation *);
#endif
