#ifndef SNOW_MARKUP_TRACE_H
#define SNOW_MARKUP_TRACE_H
#include <stdint.h>
#include <stddef.h>
#include <stdatomic.h>
/* Authored recorder for CENTRAL_IMPULSE.md, "Markup dispatch and callback
 * argument contract". This is not an installer or an object-lifetime guard.
 * Initialize once before publishing; retain storage/functions even after close
 * for cached callers. Never reopen. Providers must be bounded/thread-safe.
 * All calls must return normally; exceptions/longjmp leave recording undrained.
 * On Windows x64 this uses the native five-argument ABI. Other builds test
 * recorder semantics only. Result is opaque integer-register data, not a
 * recovered semantic return value. Raw addresses belong in private captures.
 */
typedef uintptr_t (*SnowMarkupOriginal)(void *, void *, uint32_t, uint8_t, uint32_t);
typedef uint64_t (*SnowMarkupClock)(void);
typedef struct {
    uintptr_t descriptor, receiver, owner, caller, result;
    uint64_t entry_tick, exit_tick, thread;
    uint32_t markup_id, extra;
    uint8_t value;
} SnowMarkupRecord;
typedef struct {
    SnowMarkupRecord *records;
    size_t capacity;
    SnowMarkupOriginal original;
    SnowMarkupClock clock, thread_id;
    uintptr_t owner; /* Installer-supplied identity, never dereferenced or validated. */
    atomic_uint_fast64_t gate;
    atomic_size_t used, dropped;
} SnowMarkupTrace;
int snow_markup_trace_init(SnowMarkupTrace *, SnowMarkupRecord *, size_t,
    SnowMarkupOriginal, SnowMarkupClock, SnowMarkupClock, uintptr_t);
uintptr_t snow_markup_trace_call(SnowMarkupTrace *, void *, void *, uint32_t,
    uint8_t, uint32_t, uintptr_t);
void snow_markup_trace_close(SnowMarkupTrace *);
/* Drained allows reading records, not unloading a wrapper or freeing objects.
 * Closed calls still forward, unrecorded. Empty records never prove install. */
int snow_markup_trace_drained(const SnowMarkupTrace *);
int snow_markup_trace_read(const SnowMarkupTrace *, size_t, void *, size_t);
#endif
