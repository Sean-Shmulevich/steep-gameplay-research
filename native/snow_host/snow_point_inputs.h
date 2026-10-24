#ifndef SNOW_POINT_INPUTS_H
#define SNOW_POINT_INPUTS_H
#include "snow_entry_attribution.h"
#define SNOW_POINT_DIRECTIONAL_LIMIT 32u
#define SNOW_POINT_SUMMED_LIMIT 64u
typedef struct {
    uint32_t point[4],direction[4];
    uint8_t enabled;
} SnowDirectionalInput;
typedef struct {
    uint32_t a[4],b[4],point[4];
    uint8_t kind,enabled;
} SnowSummedInput;
typedef struct {
    uint64_t actor,runtime,body,descriptor,directional_data,summed_data;
    uint64_t directional_count,summed_count;
    uint32_t basis[3][3],translation[3],local_center[3],local_inertia[3][3];
    uint32_t runtime_scale;
    uint8_t flags,kind;
    SnowDirectionalInput directional[SNOW_POINT_DIRECTIONAL_LIMIT];
    SnowSummedInput summed[SNOW_POINT_SUMMED_LIMIT];
} SnowPointInputs;
typedef struct {
    uint32_t stage,pass,reads,read_failed,count_valid;
    uint64_t directional_count,summed_count;
} SnowPointDiagnostic;
/* Diagnostic counts are partial reads, never an accepted snapshot. stage=0 means
 * accepted; stages 10..28 locate guards/reads, 30 means repeated samples differ. */
int snow_point_inputs_observe_detailed(SnowEntryRead,void *,uint64_t actor,
    uint64_t image_base,uint64_t image_size,SnowPointInputs *,SnowPointDiagnostic *);
/* Private observation layout, not a wire ABI. Basis/inertia are native columns.
 * Caller verifies image/build and fresh actor provenance. At most 768 exact
 * reads <=16 bytes. Two equal sequential samples; no atomicity/lifetime pin.
 * More than 32 directional or 64 summed records rejects; no truncation. Zero on failure.
 * No scalar gate/curve producer, live submission or native locking is inferred.
 */
int snow_point_inputs_observe(SnowEntryRead,void *,uint64_t actor,
    uint64_t image_base,uint64_t image_size,SnowPointInputs *);
#endif
