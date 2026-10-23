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
/* Resolver must establish current actor-to-action provenance, not return a
 * saved action pointer. It is bounded, non-mutating, thread-safe and returns
 * exactly 1 with a nonzero action. Its read budget is additional to the reader.
 * All callbacks/context must remain alive under the recorder lifetime contract. */
typedef int (*SnowHistoryResolve)(void *,void *,uint64_t *);
typedef struct {
    SnowEntryRead read;
    void *read_context;
    SnowHistoryResolve resolve;
    void *resolve_context;
    uint64_t table,callback,receiver_slot,fallback_clock_slot;
} SnowHistoryTraceContext;
/* Matches SnowUpdateHistoryRead. Resolves before and after a two-sample read;
 * returns only the second sample when identities and action resolution agree.
 * Invalid output is zeroed. This is observer plumbing, not a game resolver. */
int snow_history_trace_read(void *,void *,SnowHistoryActionObservation *);
#endif
