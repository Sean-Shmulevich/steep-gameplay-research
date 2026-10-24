#ifndef SNOW_MARKUP_UPDATE_PROBE_H
#define SNOW_MARKUP_UPDATE_PROBE_H
#include "snow_markup_update_trace.h"
#ifdef SNOW_MARKUP_UPDATE_PROBE_BUILD
#define SNOW_MARKUP_API __declspec(dllexport)
#else
#define SNOW_MARKUP_API
#endif
/* Experimental ABI 3. Configure never installs. Caller verifies the image,
 * original calling convention, slot, fresh component and reader provenance.
 * One configuration/install attempt; modules stay pinned for cached callers.
 * Reader/context must outlive all possible calls, not merely capture/drain.
 */
SNOW_MARKUP_API uint32_t SnowMarkupUpdateProbe_ABIVersion(void);
SNOW_MARKUP_API size_t SnowMarkupUpdateProbe_RecordSize(void);
SNOW_MARKUP_API uint64_t SnowMarkupUpdateProbe_ClockFrequency(void);
SNOW_MARKUP_API int SnowMarkupUpdateProbe_Configure(uint64_t slot_address,
    SnowMarkupUpdateOriginal,void *component_filter,SnowMarkupUpdateRead,void *);
SNOW_MARKUP_API void SnowMarkupUpdateProbe_Dispatch(void *,float);
/* Only aligned, nonexecutable image slots in the original target's module.
 * 1 success, 0 refusal/conflict, -1 protection failure. Restore after ANY
 * installation attempt, then close/drain. Restore is retryable and preserves
 * a competing slot pointer. A successful restore is not an unload barrier.
 */
SNOW_MARKUP_API int SnowMarkupUpdateProbe_InstallSlot(void);
SNOW_MARKUP_API int SnowMarkupUpdateProbe_RestoreSlot(void);
SNOW_MARKUP_API int SnowMarkupUpdateProbe_Close(size_t *,size_t *);
SNOW_MARKUP_API int SnowMarkupUpdateProbe_ReadRecordSized(size_t,void *,size_t);
#endif
