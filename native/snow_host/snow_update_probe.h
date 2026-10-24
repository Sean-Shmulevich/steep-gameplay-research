#ifndef SNOW_UPDATE_PROBE_H
#define SNOW_UPDATE_PROBE_H
#include "snow_update_snapshot.h"
/* Experimental ABI v9: caller must use this exact header/build. Configure alone installs no hook.
 * v9 adds point-input rejection diagnostics; rebuild readers.
 * Configure once BEFORE publishing Dispatch; configuration is never retried.
 * Caller verifies executable identity, original target/signature and counter owners.
 * DLL pins itself. Close stops capture, not forwarding; never free supplied objects
 * merely because capture drained. ReadRecord is available only after close+drain.
 */
#ifdef SNOW_UPDATE_PROBE_BUILD
#define SNOW_PROBE_API __declspec(dllexport)
#else
#define SNOW_PROBE_API
#endif
SNOW_PROBE_API int SnowProbe_Configure(const SnowUpdateBinding *, SnowUpdateOriginal);
/* Profile is immutable after configure. Caller verifies its build-specific route. */
SNOW_PROBE_API int SnowProbe_ConfigureAttributed(const SnowUpdateBinding *, SnowUpdateOriginal,
                                               const SnowEntryProfile *);
/* Opt-in motion channel. NULL profile disables attribution, not motion. */
SNOW_PROBE_API int SnowProbe_ConfigureObserved(const SnowUpdateBinding *, SnowUpdateOriginal,
                                             const SnowEntryProfile *, int observe_motion);
/* Optional point-input profile. Both image arguments zero disables it.
 * Caller verifies the image. Point failures do not discard ordinary snapshots. */
SNOW_PROBE_API int SnowProbe_ConfigureDetailed(const SnowUpdateBinding *, SnowUpdateOriginal,
    const SnowEntryProfile *, int observe_motion, uint64_t image_base, uint64_t image_size);
SNOW_PROBE_API void SnowProbe_Dispatch(void *, float, float);
SNOW_PROBE_API int SnowProbe_Close(size_t *used, size_t *dropped);
/* Diagnostic lifetime counters include late forwarding after Close. Each field
 * is atomic; the pair is not an atomic snapshot and drain does not freeze it.
 * Read after Restore+Close for a useful bounded-session observation, not proof
 * that a thread with a cached dispatch pointer cannot call later. */
typedef struct { uint64_t selected_calls, other_calls; } SnowProbeDispatchCounts;
SNOW_PROBE_API int SnowProbe_ReadDispatchCounts(SnowProbeDispatchCounts *);
#define SNOW_PROBE_ABI_VERSION 9u
/* Query before configure/copy. Sized reads reject incompatible record buffers. */
SNOW_PROBE_API uint32_t SnowProbe_ABIVersion(void);
SNOW_PROBE_API size_t SnowProbe_RecordSize(void);
SNOW_PROBE_API int SnowProbe_ReadRecordSized(size_t,void *,size_t);
/* Legacy exact-header entry point; prefer the sized API. */
SNOW_PROBE_API int SnowProbe_ReadRecord(size_t, SnowUpdateRecord *);
/* Explicit opt-in pointer replacement at actor_table+0x2c0. One install attempt.
 * Return 1 on success, 0 on refusal/conflict, -1 on page-protection failure.
 * Restore is retryable, never overwrites a competing pointer, and must be called
 * after ANY attempted install, including failure. Then close and drain capture.
 * Only aligned nonexecutable MEM_IMAGE slots in the original target's module
 * qualify. Module pinning retains the table/target, not the player objects.
 */
SNOW_PROBE_API int SnowProbe_InstallSlot(void);
SNOW_PROBE_API int SnowProbe_RestoreSlot(void);
#endif
