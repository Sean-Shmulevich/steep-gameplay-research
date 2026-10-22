#ifndef SNOW_ENTRY_THUNK_H
#define SNOW_ENTRY_THUNK_H
#include <stdint.h>
/* Authored Win64 entry adapter. Values are raw candidates, NOT validated identity.
 * Available only during EntryDispatch. Copy/dereference guarded data there;
 * range_slot points into a worker frame whose contents can change on next claim.
 * EntryDispatch must preserve the Win64 ABI and return normally.
 * This module does not install a hook, forward to the game, or establish lifetime.
 */
typedef struct {
    uint64_t job, range_slot, local_index, return_address, entry_rsp;
} SnowEntryRegisters;
void SnowProbe_EntryThunk(void *actor, float elapsed, float consumed);
void SnowProbe_EntryDispatch(void *actor, float elapsed, float consumed,
                             const SnowEntryRegisters *entry);
#endif
