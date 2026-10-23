#ifndef SNOW_ACTION_PROBE_H
#define SNOW_ACTION_PROBE_H
#include "snow_action_trace.h"
#ifdef SNOW_ACTION_PROBE_BUILD
#define SNOW_ACTION_API __declspec(dllexport)
#else
#define SNOW_ACTION_API
#endif
/* Experimental ABI 2 (optional vector/status samples; rebuild readers). Caller verifies executable, slot, signature and action
 * provenance. Configure does not install. Exactly one configuration/install
 * attempt; DLL and target module remain pinned for late dispatch callers.
 * Captures all objects using this slot; no selected-player attribution implied.
 */
SNOW_ACTION_API uint32_t SnowActionProbe_ABIVersion(void);
SNOW_ACTION_API size_t SnowActionProbe_RecordSize(void);
SNOW_ACTION_API uint64_t SnowActionProbe_ClockFrequency(void);
SNOW_ACTION_API int SnowActionProbe_Configure(uint64_t slot_address,SnowActionOriginal);
/* Observers/context must remain valid for all callers, including late dispatch.
 * NULL disables sampling. Event timestamps encompass observation overhead. */
SNOW_ACTION_API int SnowActionProbe_ConfigureObserved(uint64_t,SnowActionOriginal,SnowActionRead,void *);
SNOW_ACTION_API void SnowActionProbe_Dispatch(void *);
/* Only nonexecutable aligned image slots in original target's module qualify.
 * 1 success, 0 refusal/conflict, -1 protection failure. Restore after ANY attempt,
 * then close/drain. Restoration is retryable and preserves competing pointers.
 */
SNOW_ACTION_API int SnowActionProbe_InstallSlot(void);
SNOW_ACTION_API int SnowActionProbe_RestoreSlot(void);
SNOW_ACTION_API int SnowActionProbe_Close(size_t *,size_t *);
SNOW_ACTION_API int SnowActionProbe_ReadRecordSized(size_t,void *,size_t);
#endif
