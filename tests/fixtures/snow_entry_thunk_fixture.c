#include "snow_entry_thunk.h"
#include <stddef.h>
_Static_assert(sizeof(SnowEntryRegisters)==40,"assembly snapshot size");
_Static_assert(offsetof(SnowEntryRegisters,entry_rsp)==32,"assembly snapshot layout");
__declspec(dllexport) volatile uint64_t observed_entry[8];
__declspec(dllexport) void SnowProbe_EntryThunk(void *,float,float);
void SnowProbe_EntryDispatch(void *actor,float elapsed,float consumed,
                            const SnowEntryRegisters *entry) {
    union { float value; uint32_t bits; } a={elapsed},b={consumed};
    observed_entry[0]=entry->job;
    observed_entry[1]=entry->range_slot;
    observed_entry[2]=entry->local_index;
    observed_entry[3]=entry->return_address;
    observed_entry[4]=entry->entry_rsp;
    observed_entry[5]=(uint64_t)(uintptr_t)actor;
    observed_entry[6]=a.bits;
    observed_entry[7]=b.bits;
}
