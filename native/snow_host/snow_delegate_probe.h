#ifndef SNOW_DELEGATE_PROBE_H
#define SNOW_DELEGATE_PROBE_H
#include "snow_delegate_trace.h"
#ifdef SNOW_DELEGATE_PROBE_BUILD
#define SNOW_DELEGATE_API __declspec(dllexport)
#else
#define SNOW_DELEGATE_API
#endif
/* Experimental graphics-main ABI v1. Caller verifies build/code identity and
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
SNOW_DELEGATE_API uint32_t SnowDelegateProbe_ABIVersion(void);
SNOW_DELEGATE_API size_t SnowDelegateProbe_RecordSize(void);
SNOW_DELEGATE_API int SnowDelegateProbe_Configure(const SnowDelegateBinding *);
SNOW_DELEGATE_API int SnowDelegateProbe_Install(void);
SNOW_DELEGATE_API int SnowDelegateProbe_Restore(void);
SNOW_DELEGATE_API int SnowDelegateProbe_Close(size_t *,size_t *);
SNOW_DELEGATE_API int SnowDelegateProbe_Read(size_t,void *,size_t);
#endif
