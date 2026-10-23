#ifndef SNOW_COMMAND_OBSERVATION_H
#define SNOW_COMMAND_OBSERVATION_H
#include "snow_delegate_trace.h"
/* Authored kind-3 command observer using the recovered four-qword descriptor.
 * This does not publish a command, install a hook, or establish engine phase.
 * One initialize only. Owner, recorder, code and providers must survive ALL
 * potential deliveries, including cached repeats after capture is closed.
 * Close/drained authorize reading records, never freeing or unloading storage.
 * No allocation, engine calls, locks or gameplay writes in our callback body.
 * Providers inherit snow_delegate_trace's bounded/nonrecursive requirements.
 * Intended native ABI: Windows x64. Host tests exercise plumbing only.
 */
typedef struct {
    uintptr_t body, auxiliary, context, invoker;
} SnowCommandDescriptor;
typedef struct {
    SnowDelegateTrace trace;
    uint64_t request_id;
} SnowCommandObservation;
/* request_id must be nonzero and fit uintptr_t. The recorded result is this
 * authored ID; it is not the game's command result or completion receipt.
 * Descriptor source may be copied; owner storage must remain stable.
 */
int snow_command_observation_init(SnowCommandObservation *, SnowCommandDescriptor *,
    uint64_t request_id, SnowDelegateRecord *, size_t,
    SnowDelegateClock clock, SnowDelegateClock thread_id);
#endif
