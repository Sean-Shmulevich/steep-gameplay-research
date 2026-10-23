/* Authored diagnostic for copied float32 fields; preserves finite-only policy. */
#ifndef SNOW_FINITE_DIAGNOSTIC_H
#define SNOW_FINITE_DIAGNOSTIC_H
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static inline int snow_nonfinite_field(const float *values, size_t count,
                                       const char *field, char *why, size_t size) {
    for (size_t i = 0; i < count; ++i) {
        if (!isfinite(values[i])) {
            uint32_t bits;
            memcpy(&bits, &values[i], sizeof bits);
            snprintf(why, size, "nonfinite %s[%zu] bits=%08x", field, i, (unsigned)bits);
            return 1;
        }
    }
    return 0;
}
#endif
