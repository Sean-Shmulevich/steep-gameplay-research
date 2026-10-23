#ifndef SNOW_CONTINUATION_IDENTITY_H
#define SNOW_CONTINUATION_IDENTITY_H
#include <stdint.h>
/* Authored structural matcher for the observed detour arrangement. No memory
 * reads, code execution, pointer retention or lifetime guarantee. Byte samples
 * must be collected and revalidated by the caller in the current process. */
typedef struct {
    uintptr_t entry, candidate, expected_handler;
    unsigned char entry_bytes[32], candidate_bytes[35];
} SnowContinuationSample;
int snow_continuation_matches(const SnowContinuationSample *sample,
    uint64_t prefix_hash,uint64_t continuation_hash);
#endif
