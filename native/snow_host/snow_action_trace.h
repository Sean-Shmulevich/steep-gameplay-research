#ifndef SNOW_ACTION_TRACE_H
#define SNOW_ACTION_TRACE_H
#include <stddef.h>
#include <stdint.h>
#include <stdatomic.h>
/* Authored evaluator-call recorder; no hook installation or game layout.
 * Adapter must verify a void evaluator taking one action pointer. This interface
 * is not suitable for arbitrary engine calls or callbacks with a return value.
 * Initialize once before publication; retain recorder, callbacks and original
 * for every possible late caller. Close/drain does NOT authorize unloading.
 * Clock/thread callbacks must be bounded, thread-safe, non-reentrant and return
 * normally. Original may recurse; nonlocal exits leave drain incomplete.
 * Use the same verified clock domain as the update trace for correlation.
 */
typedef void (*SnowActionOriginal)(void *);
typedef uint64_t (*SnowActionClock)(void);
typedef struct {
    uintptr_t action;
    uint64_t entry_tick, exit_tick, thread;
} SnowActionRecord;
typedef struct {
    SnowActionRecord *records;
    size_t capacity;
    SnowActionOriginal original;
    SnowActionClock clock, thread_id;
    atomic_uint_fast64_t gate;
    atomic_size_t used, dropped;
} SnowActionTrace;
int snow_action_trace_init(SnowActionTrace *,SnowActionRecord *,size_t,
                          SnowActionOriginal,SnowActionClock,SnowActionClock);
void snow_action_trace_call(SnowActionTrace *,void *);
void snow_action_trace_close(SnowActionTrace *);
int snow_action_trace_drained(const SnowActionTrace *);
/* Exact-size copy only after close and drain; refusal leaves output untouched.
 * Slot order is reservation order, not timestamp order or engine causality. */
int snow_action_trace_read(const SnowActionTrace *,size_t,void *,size_t);
#endif
