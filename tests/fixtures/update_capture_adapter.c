/* Synthetic provider only. No process discovery or game offsets are inferred. */
#include "steep_probe_binding.h"
static SnowUpdateBinding saved;
static SnowUpdateOriginal target;
__declspec(dllexport) void FixtureBinding(const SnowUpdateBinding *b,SnowUpdateOriginal original) { saved=*b; target=original; }
int snow_steep_probe_binding(SnowUpdateBinding *out,SnowUpdateOriginal *original,char *why,size_t n) {
    (void)why; (void)n; *out=saved; *original=target; return target ? 0 : 1;
}
