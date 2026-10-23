#ifndef SNOW_DELEGATE_PROBE_H
#define SNOW_DELEGATE_PROBE_H
#include "snow_delegate_trace.h"
#ifdef SNOW_DELEGATE_PROBE_BUILD
#define SNOW_DELEGATE_API __declspec(dllexport)
#else
#define SNOW_DELEGATE_API
#endif
/* Experimental main-delegate record ABI v3. Caller verifies build/code identity and
 * guarantees owner storage remains allocated and unreused during Configure,
 * Install and Restore, and preserves the function/context ABI for cached callers.
 * Guards/CAS do NOT establish these lifetime and binding prerequisites.
 * Configure once; one install attempt; Restore is retryable and conflict-aware.
 * This module and original image are pinned. Never unload/reuse recorder state.
 */
typedef struct {
    uint64_t owner_global, owner, job_table, dispatch_method;
    uint64_t function, auxiliary, context, invoker;
} SnowDelegateBinding;
/* Fixed inspected layouts only; this is not an arbitrary-offset hook API. */
typedef enum { SNOW_DELEGATE_GRAPHICS_MAIN=1, SNOW_DELEGATE_ENGINE_MAIN=2 } SnowDelegateSite;
SNOW_DELEGATE_API int SnowDelegateProbe_ConfigureSite(const SnowDelegateBinding *, SnowDelegateSite);
/* Legacy Configure selects GRAPHICS_MAIN. Record layout/version unchanged. */
SNOW_DELEGATE_API uint32_t SnowDelegateProbe_ABIVersion(void);
SNOW_DELEGATE_API size_t SnowDelegateProbe_RecordSize(void);
SNOW_DELEGATE_API int SnowDelegateProbe_Configure(const SnowDelegateBinding *);
SNOW_DELEGATE_API int SnowDelegateProbe_Install(void);
SNOW_DELEGATE_API int SnowDelegateProbe_Restore(void);
SNOW_DELEGATE_API int SnowDelegateProbe_Close(size_t *,size_t *);
SNOW_DELEGATE_API int SnowDelegateProbe_Read(size_t,void *,size_t);
/* One optional authored observation delivered by the next intercepted delegate.
 * Arm after Configure, before Install; one attempt, never rearm. Does not submit
 * to the native command queue or authorize gameplay mutation. Module/storage
 * remain resident. Read succeeds only after the forwarding invocation returns.
 * Manager samples are sequential read-only pointers, not ownership or snapshots.
 */
typedef struct {
    uint64_t request_id, entry_tick, exit_tick, thread, caller, receiver, storage;
    uint64_t manager_before, manager_after, result;
    uint32_t valid_before, valid_after;
} SnowDelegateRequestObservation;
SNOW_DELEGATE_API int SnowDelegateProbe_ArmObservation(uint64_t request_id);
SNOW_DELEGATE_API int SnowDelegateProbe_ReadObservation(SnowDelegateRequestObservation *);
#endif
