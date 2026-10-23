#ifndef SNOW_HISTORY_OBSERVATION_H
#define SNOW_HISTORY_OBSERVATION_H
#include "snow_update_trace.h"
typedef struct {
    uint64_t action, table, callback, receiver_slot, fallback_clock_slot;
} SnowHistoryProfile;
typedef struct {
    SnowHistoryActionObservation samples[2];
    uint32_t reads, bytes, identities_match, dynamic_equal;
} SnowHistoryCapture;
/* Return 1 for matching identities/settings, 2 for changed identities/settings,
 * 0 for invalid/unavailable/unsupported reads (samples cleared). Two dynamic
 * samples are retained on 1/2. At most 32 reads and 1024 bytes. This does not
 * prove atomicity, lifetime, execution, freshness or actor/action ownership.
 * Caller verifies build and resolves fresh action provenance before each call.
 * No game calls, writes, polling or native recorder enablement. */
int snow_history_observe(SnowEntryRead,void *,const SnowHistoryProfile *,SnowHistoryCapture *);
#endif
