#ifndef STEEP_PROBE_BINDING_H
#define STEEP_PROBE_BINDING_H
#include "snow_update_snapshot.h"
/* Authored integration for the analyzed build. Call on the adapter's serialized
 * executor while the host holds simulation. Reads only; no hook installation.
 * Returns 0 on success. Output is zero on failure. Does not pin object lifetime.
 * Compile/link snow_update_snapshot.c with steep_adapter.c when using this API. */
int snow_steep_probe_binding(SnowUpdateBinding *, SnowUpdateOriginal *, char *, size_t);
#endif
