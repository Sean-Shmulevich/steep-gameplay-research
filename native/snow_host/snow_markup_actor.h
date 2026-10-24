#ifndef SNOW_MARKUP_ACTOR_H
#define SNOW_MARKUP_ACTOR_H
#include "snow_entry_attribution.h"
/* Authored private snapshot. No interpretation of state numbers as sport names. */
typedef struct {
    uint64_t actor,entity,world,runtime,state_owner,state_child;
    uint32_t current_mode,outer_state,inner_state,outer_present,inner_present;
    uint32_t world_interval_bits,pending_bits[4],normal_bits[4],current_bits[4];
    uint32_t runtime_present,gain_state;
    uint64_t vector_receiver,vector_owner,gain_handle,gain_payload;
    uint32_t projection_inputs_present,direction_bits[4],projection_gain_bits,gain_status;
    uint8_t reverse_fallback,fc9,fdc;
} SnowMarkupActorSnapshot;
/* Fresh actor provenance and image verification belong to caller. Two equal
 * sequential samples required; no atomicity or pin. Output zeroed on refusal.
 * At most 72 exact reads, each <=16 bytes; no writes/game calls/allocations.
 */
int snow_markup_actor_observe(SnowEntryRead,void *,uint64_t actor,
    uint64_t image_base,uint64_t image_size,SnowMarkupActorSnapshot *);
#endif
