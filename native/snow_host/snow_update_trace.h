#ifndef SNOW_UPDATE_TRACE_H
#define SNOW_UPDATE_TRACE_H
#include <stdint.h>
#include <stddef.h>
#include <stdatomic.h>
#include "snow_batch_frame.h"
#include "snow_motion_observation.h"
#include "snow_point_inputs.h"
/* Authored capture plumbing. No installation, game offsets, or ownership claims.
 * Initialize once before publishing. Context, records and callbacks must remain
 * alive for ALL callers, including calls after close. Never reopen/reinitialize.
 * Callbacks must return normally; nonlocal exits leave drain incomplete.
 * Snapshot callback must be non-mutating, bounded, thread-safe and not recurse.
 */
typedef struct {
    uint64_t runtime, main_body, rider_body, request, substep;
    uint32_t valid;
    unsigned char gates[4];
    int32_t preconsume_counter;
    float preconsume_timers[2];
    float pending[4], linear[2][3], angular[2][3], inverse_mass[2];
    uint32_t point_attempted, point_valid;
    uint64_t point_read_ticks;
    SnowPointInputs point_inputs;
    SnowPointDiagnostic point_diagnostic;
} SnowUpdateSnapshot;
/* Authored observation payload, not a native game object or public wire ABI.
 * All pointers are session-private provenance. No generation/freshness claim.
 * Producers preserve float bits and supply their own bounded identity guards. */
typedef struct {
    uint64_t action, owner, configuration, history, clock_record;
    uint64_t receiver, selected, history_times[3], clock_ticks;
    uint64_t start_time, repeat_time;
    uint32_t channel, direction_kind, mode, hold_delay_bits, repeat_delay_bits;
    uint32_t reference_bits[4], history_b_bits[4], history_c_bits[4];
    uint32_t threshold_bits, history_magnitude_bits, action_magnitude_bits;
    uint8_t active, previous;
} SnowHistoryActionObservation;
typedef struct {
    uintptr_t actor;
    uint64_t entry_tick, exit_tick, thread;
    float elapsed, derivative;
    SnowUpdateSnapshot before, after;
    uint32_t attribution_attempted, attribution_valid;
    SnowEntryAttribution attribution;
    uint32_t frame_valid;
    SnowBatchFrame frame;
    uint32_t motion_attempted, motion_before_valid, motion_after_valid;
    SnowMotionObservation motion_before, motion_after;
    uint32_t history_attempted, history_before_valid, history_after_valid;
    SnowHistoryActionObservation history_before, history_after;
} SnowUpdateRecord;
typedef void (*SnowUpdateOriginal)(void *, float, float);
typedef void (*SnowUpdateRead)(void *, SnowUpdateSnapshot *);
typedef uint64_t (*SnowUpdateClock)(void);
typedef struct {
    SnowUpdateRecord *records;
    size_t capacity;
    SnowUpdateOriginal original;
    SnowUpdateRead read;
    SnowUpdateClock clock, thread_id;
    atomic_uint_fast64_t gate; /* high bit closed, remaining bits active */
    atomic_size_t used, dropped;
} SnowUpdateTrace;
int snow_trace_init(SnowUpdateTrace *, SnowUpdateRecord *, size_t,
                    SnowUpdateOriginal, SnowUpdateRead, SnowUpdateClock, SnowUpdateClock);
void snow_trace_call(SnowUpdateTrace *, void *, float, float);
/* Optional bounded, non-mutating callback runs only for reserved records, before
 * original. Return 1 for job attribution, 3 for job plus frame; other values clear output and never
 * suppresses original. Context is invocation-local; it must not escape the call.
 * Callback must return normally and must not recursively invoke this trace. */
typedef int (*SnowUpdateEntryRead)(void *, SnowEntryAttribution *, SnowBatchFrame *);
void snow_trace_call_attributed(SnowUpdateTrace *, void *, float, float,
                                SnowUpdateEntryRead, void *);
/* Independent optional channel, sampled around original. Return exactly 1 for
 * valid output; other returns clear that sample only. Same bounded/non-mutating
 * callback requirements as entry observation. No exception containment. */
typedef int (*SnowUpdateMotionRead)(void *, void *, SnowMotionObservation *);
void snow_trace_call_observed(SnowUpdateTrace *, void *, float, float,
                             SnowUpdateEntryRead, void *, SnowUpdateMotionRead, void *);
/* Optional history channel. Return exactly 1 for a valid guarded sample.
 * Invalid output is discarded independently before/after. Callback must be
 * bounded, non-mutating, thread-safe, non-recursive and return normally.
 * It must resolve fresh action provenance for this actor; no saved heap pointers.
 * Samples bracket original but do not count producer/evaluator executions.
 * No installation or concrete memory reader is supplied by this interface. */
typedef int (*SnowUpdateHistoryRead)(void *, void *, SnowHistoryActionObservation *);
void snow_trace_call_with_history(SnowUpdateTrace *, void *, float, float,
    SnowUpdateEntryRead, void *, SnowUpdateMotionRead, void *,
    SnowUpdateHistoryRead, void *);
void snow_trace_close(SnowUpdateTrace *);
/* Records may be read only after this returns true. It does NOT permit unloading
 * the wrapper/context: a cached caller can still enter and forward to original. */
int snow_trace_drained(const SnowUpdateTrace *);
/* Exact-size copy after close+drain. Refusal leaves caller storage untouched.
 * The caller still owns output allocation/lifetime and recorder lifetime. */
int snow_trace_read_record(const SnowUpdateTrace *,size_t,void *,size_t);
#endif
