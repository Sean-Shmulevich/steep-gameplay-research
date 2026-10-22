#ifndef SNOW_BATCH_FRAME_H
#define SNOW_BATCH_FRAME_H
#include "snow_entry_attribution.h"
typedef struct {
    uint64_t timing_owner, world, outer_completion_counter;
    uint32_t ordinal, selected_count, elapsed_bits, consumed_bits;
} SnowBatchFrame;
/* Caller must first validate the live job route with snow_entry_attribute.
 * Build-specific first-batch stack layout. Expected world comes from independent
 * player/world binding; timing bits come from actual callback arguments.
 * At most 16 exact reads. Output cleared on failure. No lifetime pinning, ABA
 * detection or global invocation uniqueness. Counter is world+0x20, NOT the
 * existing trace request counter. No writes or native function calls. */
int snow_batch_frame(SnowEntryRead,void *,uint64_t job,uint64_t expected_return,
                     uint64_t expected_world,uint32_t elapsed_bits,
                     uint32_t consumed_bits,SnowBatchFrame *);
#endif
