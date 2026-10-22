#ifndef SNOW_UPDATE_PROBE_H
#define SNOW_UPDATE_PROBE_H
#include "snow_update_snapshot.h"
/* Experimental ABI v1: caller must use this exact header/build. No hook is installed.
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
SNOW_PROBE_API void SnowProbe_Dispatch(void *, float, float);
SNOW_PROBE_API int SnowProbe_Close(size_t *used, size_t *dropped);
SNOW_PROBE_API int SnowProbe_ReadRecord(size_t, SnowUpdateRecord *);
#endif
