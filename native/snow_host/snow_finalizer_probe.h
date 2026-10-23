#ifndef SNOW_FINALIZER_PROBE_H
#define SNOW_FINALIZER_PROBE_H
#include "snow_delegate_trace.h"
#ifdef SNOW_FINALIZER_PROBE_BUILD
#define SNOW_FINALIZER_API __declspec(dllexport)
#else
#define SNOW_FINALIZER_API
#endif
/* Experimental ABI 1, one-pointer integer-result forwarding. Caller must verify
 * build and finalizer ABI. Not suitable for arbitrary virtual functions.
 * ABI 1 uses the current delegate record layout (including before/after job
 * fields). Any future record layout change must bump this ABI as well.
 * Selected job is owner+0x218; shared image table slot is +0x70. All other jobs
 * forward without capture. Guards do not pin owner lifetime or exclude ABA.
 * Configure once, install once, restore retryably, then close/drain. Always
 * restore after an install attempt. Module/image remain pinned through exit.
 * No plugin callbacks. The original may run while scheduler locks are held.
 */
typedef uintptr_t (*SnowFinalizerOriginal)(void *job);
typedef struct { uint64_t owner_global, owner, job_table, original; } SnowFinalizerBinding;
SNOW_FINALIZER_API uint32_t SnowFinalizerProbe_ABIVersion(void);
SNOW_FINALIZER_API size_t SnowFinalizerProbe_RecordSize(void);
SNOW_FINALIZER_API int SnowFinalizerProbe_Configure(const SnowFinalizerBinding *);
/* 1 success, 0 refusal/conflict, -1 protection failure. */
SNOW_FINALIZER_API int SnowFinalizerProbe_Install(void);
SNOW_FINALIZER_API int SnowFinalizerProbe_Restore(void);
SNOW_FINALIZER_API int SnowFinalizerProbe_Close(size_t *,size_t *);
SNOW_FINALIZER_API int SnowFinalizerProbe_Read(size_t,void *,size_t);
#endif
