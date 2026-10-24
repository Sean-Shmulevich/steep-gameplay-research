#ifndef SNOW_MARKUP_UPDATE_TRACE_H
#define SNOW_MARKUP_UPDATE_TRACE_H
#include <stdint.h>
#include <stddef.h>
#include "snow_markup_provider.h"
#include <stdatomic.h>
/* Authored receiver-plus-float update recorder. Forwards the float argument
 * unchanged and records its raw bits. No return-value ABI claim: the inspected
 * phase caller ignores the return. Sample semantics belong to the supplied reader. Installation/caller verification remains external.
 * Initialize once before publication and retain everything for cached callers
 * even after close/drain. Nonlocal exits leave the trace undrained.
 * Clock/thread providers must be bounded, thread-safe, nonrecursive and return
 * normally. Their timestamps include observation overhead.
 */
typedef void (*SnowMarkupUpdateOriginal)(void *,float);
typedef uint64_t (*SnowMarkupUpdateClock)(void);
/* Return exactly 1 for accepted sample; all other values clear that sample.
 * Reader must be bounded, non-mutating, thread-safe, nonrecursive and return
 * normally. It must acquire/verify fresh ownership, not reuse heap addresses.
 */
typedef int (*SnowMarkupUpdateRead)(void *,void *,SnowMarkupUpdateSnapshot *);
typedef struct {
    uintptr_t component,caller;
    uint32_t argument_bits;
    uint64_t entry_tick,exit_tick,thread;
    uint32_t before_valid,after_valid;
    SnowMarkupUpdateSnapshot before,after;
} SnowMarkupUpdateRecord;
typedef struct {
    SnowMarkupUpdateRecord *records;
    size_t capacity;
    SnowMarkupUpdateOriginal original;
    SnowMarkupUpdateClock clock,thread_id;
    SnowMarkupUpdateRead read;
    void *read_context;
    atomic_uint_fast64_t gate;
    atomic_size_t used,dropped;
} SnowMarkupUpdateTrace;
int snow_markup_update_trace_init(SnowMarkupUpdateTrace *,SnowMarkupUpdateRecord *,size_t,
    SnowMarkupUpdateOriginal,SnowMarkupUpdateClock,SnowMarkupUpdateClock,
    SnowMarkupUpdateRead,void *);
void snow_markup_update_trace_call(SnowMarkupUpdateTrace *,void *,float,uintptr_t caller);
void snow_markup_update_trace_close(SnowMarkupUpdateTrace *);
int snow_markup_update_trace_drained(const SnowMarkupUpdateTrace *);
/* Exact-size read only after close+drain. Refusal leaves output unchanged.
 * Reservation order is not execution/completion order. Records are private.
 * Close/drain allows reads, NOT unloading or freeing callbacks/context.
 */
int snow_markup_update_trace_read(const SnowMarkupUpdateTrace *,size_t,void *,size_t);
#endif
