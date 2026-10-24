#ifndef SNOW_FRAME_INPUTS_H
#define SNOW_FRAME_INPUTS_H
#include "snow_entry_attribution.h"
typedef struct {
    uint64_t actor, runtime, receiver, receiver_table, callback, owner, config;
    uint32_t physical_mode, elapsed;
    uint32_t cached_basis[3][4], forward[4][4], inverse[4][4];
} SnowFrameInputs;
/* Build-specific, read-only observer: at most 46 exact reads of <=16 bytes.
 * Requires two identical samples, not atomicity, phase attribution or lifetime
 * pinning. Caller supplies fresh actor provenance and trusted image bounds.
 * Float lanes retain raw bits. Pointers are private session identities.
 * Receiver table/slot must be inside the image; callback is never invoked.
 * Output is zero on failure. No hooks, writes or game launch.
 */
int snow_frame_inputs_observe(SnowEntryRead,void *,uint64_t actor,
    uint64_t image_base,uint64_t image_size,SnowFrameInputs *);
#endif
