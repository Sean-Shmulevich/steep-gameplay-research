#ifndef SNOW_ANIMATION_QUEUE_TRACE_H
#define SNOW_ANIMATION_QUEUE_TRACE_H
#include "snow_animation_queue.h"
#include <stdatomic.h>
/* Authored one-receiver dispatch recorder. Preserves the integer return bits;
 * no floating/vector return ABI claim. The inspected batch visitor ignores
 * the callback result. Installation/caller verification remains external.
 * Initialize once before publication and retain everything for cached callers
 * even after close/drain. Nonlocal exits leave the trace undrained.
 * Clock/thread providers must be bounded, thread-safe, nonrecursive and return
 * normally. Their timestamps include observation overhead.
 */
typedef uintptr_t (*SnowAnimationQueueOriginal)(void *);
typedef uint64_t (*SnowAnimationQueueClock)(void);
/* Return exactly 1 for accepted sample; all other values clear that sample.
 * Reader must be bounded, non-mutating, thread-safe, nonrecursive and return
 * normally. It must acquire/verify fresh ownership, not reuse heap addresses.
 */
typedef int (*SnowAnimationQueueRead)(void *,void *,SnowAnimationQueueSnapshot *);
typedef struct {
    uintptr_t component,caller,result;
    uint64_t entry_tick,exit_tick,thread;
    uint32_t before_valid,after_valid;
    SnowAnimationQueueSnapshot before,after;
} SnowAnimationQueueRecord;
typedef struct {
    SnowAnimationQueueRecord *records;
    size_t capacity;
    SnowAnimationQueueOriginal original;
    SnowAnimationQueueClock clock,thread_id;
    SnowAnimationQueueRead read;
    void *read_context;
    atomic_uint_fast64_t gate;
    atomic_size_t used,dropped;
} SnowAnimationQueueTrace;
int snow_animation_queue_trace_init(SnowAnimationQueueTrace *,SnowAnimationQueueRecord *,size_t,
    SnowAnimationQueueOriginal,SnowAnimationQueueClock,SnowAnimationQueueClock,
    SnowAnimationQueueRead,void *);
uintptr_t snow_animation_queue_trace_call(SnowAnimationQueueTrace *,void *,uintptr_t caller);
void snow_animation_queue_trace_close(SnowAnimationQueueTrace *);
int snow_animation_queue_trace_drained(const SnowAnimationQueueTrace *);
/* Exact-size read only after close+drain. Refusal leaves output unchanged.
 * Reservation order is not execution/completion order. Records are private.
 * Close/drain allows reads, NOT unloading or freeing callbacks/context.
 */
int snow_animation_queue_trace_read(const SnowAnimationQueueTrace *,size_t,void *,size_t);
#endif
