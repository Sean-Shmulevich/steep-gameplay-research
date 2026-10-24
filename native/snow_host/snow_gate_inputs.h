#ifndef SNOW_GATE_INPUTS_H
#define SNOW_GATE_INPUTS_H
#include "snow_entry_attribution.h"
typedef struct {
    uint64_t actor, runtime, shape, config;
    uint32_t immersion, alternate, activity, timer, elapsed, total_volume;
    uint32_t refill_divisor, duration, lower_other, lower_one;
} SnowGateInputs;
/* Build-specific read-only observation. Caller establishes fresh actor provenance.
 * Scalars are raw float32 bits, including nonfinite values. At most 26 reads,
 * each <=16 bytes; requires two identical samples, not atomicity or lifetime pin.
 * No hooks, writes, gate-stack values or submission-time attribution. Output is
 * zero on failure. Pointer fields are private session identities, not API handles.
 */
int snow_gate_inputs_observe(SnowEntryRead, void *, uint64_t actor,
    uint64_t image_base, uint64_t image_size, SnowGateInputs *);
#endif
