#ifndef SNOW_ANIMATION_QUEUE_PROBE_H
#define SNOW_ANIMATION_QUEUE_PROBE_H
#include "snow_animation_queue_trace.h"
#ifdef SNOW_ANIMATION_QUEUE_PROBE_BUILD
#define SNOW_QUEUE_API __declspec(dllexport)
#else
#define SNOW_QUEUE_API
#endif
/* Experimental ABI 1. Configure never installs. Caller verifies the image,
 * original calling convention, slot, fresh component and reader provenance.
 * One configuration/install attempt; modules stay pinned for cached callers.
 * Reader/context must outlive all possible calls, not merely capture/drain.
 */
SNOW_QUEUE_API uint32_t SnowAnimationQueueProbe_ABIVersion(void);
SNOW_QUEUE_API size_t SnowAnimationQueueProbe_RecordSize(void);
SNOW_QUEUE_API uint64_t SnowAnimationQueueProbe_ClockFrequency(void);
SNOW_QUEUE_API int SnowAnimationQueueProbe_Configure(uint64_t slot_address,
    SnowAnimationQueueOriginal,void *component_filter,SnowAnimationQueueRead,void *);
SNOW_QUEUE_API uintptr_t SnowAnimationQueueProbe_Dispatch(void *);
/* Only aligned, nonexecutable image slots in the original target's module.
 * 1 success, 0 refusal/conflict, -1 protection failure. Restore after ANY
 * installation attempt, then close/drain. Restore is retryable and preserves
 * a competing slot pointer. A successful restore is not an unload barrier.
 */
SNOW_QUEUE_API int SnowAnimationQueueProbe_InstallSlot(void);
SNOW_QUEUE_API int SnowAnimationQueueProbe_RestoreSlot(void);
SNOW_QUEUE_API int SnowAnimationQueueProbe_Close(size_t *,size_t *);
SNOW_QUEUE_API int SnowAnimationQueueProbe_ReadRecordSized(size_t,void *,size_t);
#endif
