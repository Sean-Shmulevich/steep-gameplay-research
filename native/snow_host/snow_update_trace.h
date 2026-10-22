#ifndef SNOW_UPDATE_TRACE_H
#define SNOW_UPDATE_TRACE_H
#include <stdint.h>
#include <stddef.h>
#include <stdatomic.h>
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
} SnowUpdateSnapshot;
typedef struct {
    uintptr_t actor;
    uint64_t entry_tick, exit_tick, thread;
    float elapsed, derivative;
    SnowUpdateSnapshot before, after;
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
void snow_trace_close(SnowUpdateTrace *);
/* Records may be read only after this returns true. It does NOT permit unloading
 * the wrapper/context: a cached caller can still enter and forward to original. */
int snow_trace_drained(const SnowUpdateTrace *);
#endif
