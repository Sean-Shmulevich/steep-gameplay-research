#ifndef SNOW_DELEGATE_TRACE_H
#define SNOW_DELEGATE_TRACE_H
#include <stdint.h>
#include <stddef.h>
#include <stdatomic.h>
/* Authored observation plumbing for the inspected two-argument invoker ABI.
 * No hook installation or native object ownership. Initialize exactly once,
 * before publishing, and retain trace/storage/functions for every possible
 * caller, including cached callers after Close. Never reopen or reinitialize.
 * All functions must return normally. Exceptions/longjmp leave capture undrained.
 * Clock and thread providers must be bounded, thread-safe and nonrecursive.
 * uintptr_t preserves the integer result; no floating/vector return ABI claim.
 * Record addresses are session-private and must not be published as raw dumps.
 */
typedef uintptr_t (*SnowDelegateOriginal)(void *function_storage, void *receiver);
typedef uint64_t (*SnowDelegateClock)(void);
typedef struct {
    uintptr_t function_storage, receiver, result;
    uint64_t entry_tick, exit_tick, thread;
} SnowDelegateRecord;
typedef struct {
    SnowDelegateRecord *records;
    size_t capacity;
    SnowDelegateOriginal original;
    SnowDelegateClock clock, thread_id;
    atomic_uint_fast64_t gate;
    atomic_size_t used, dropped;
} SnowDelegateTrace;
int snow_delegate_trace_init(SnowDelegateTrace *, SnowDelegateRecord *, size_t,
    SnowDelegateOriginal, SnowDelegateClock, SnowDelegateClock);
uintptr_t snow_delegate_trace_call(SnowDelegateTrace *, void *, void *);
void snow_delegate_trace_close(SnowDelegateTrace *);
/* Drain permits record reads only. It does not prove no future forwarding call,
 * no game dispatch, no cached pointer, or safe module/object destruction. */
int snow_delegate_trace_drained(const SnowDelegateTrace *);
int snow_delegate_trace_read(const SnowDelegateTrace *, size_t, void *, size_t);
#endif
