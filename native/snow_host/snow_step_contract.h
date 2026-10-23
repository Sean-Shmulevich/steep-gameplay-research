#ifndef SNOW_STEP_CONTRACT_H
#define SNOW_STEP_CONTRACT_H
#include <stdint.h>
/* These are last-run request identifiers, NOT execution counts. Identifier
 * gaps may include paused frames. This proves a changed token followed by a
 * stable token and re-armed hold; exact callback count needs an event recorder.
 * Full uint32 wrap aliases remain indistinguishable from unchanged tokens. */
static inline int snow_step_release_stable(uint32_t before, uint32_t released,
                                           uint32_t after, int held) {
    return released!=before && after==released && held;
}
#endif
