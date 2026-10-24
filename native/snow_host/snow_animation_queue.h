#ifndef SNOW_ANIMATION_QUEUE_H
#define SNOW_ANIMATION_QUEUE_H
#include "snow_entry_attribution.h"
#define SNOW_ANIMATION_QUEUE_LIMIT 8
/* Authored observation records, not a game layout or stable wire ABI.
 * Raw addresses are session-private. Caller verifies image/build, fresh owner,
 * component provenance and process identity; reader must be exact and bounded.
 * No game calls, writes, allocation, lifetime pin or callback installation.
 */
typedef struct {
    uint64_t event, table, handler, handles[2], payloads[2];
    uint32_t status[2];
    uint8_t table_in_image, handler_in_image;
} SnowAnimationQueueRow;
typedef struct {
    uint64_t component, owner, arrays[3];
    uint16_t headers[3], counts[3];
    SnowAnimationQueueRow rows[SNOW_ANIMATION_QUEUE_LIMIT];
} SnowAnimationQueueSnapshot;
/* Two sequential equal samples required; refusal zeroes output. Count >8,
 * parallel-count mismatch, malformed pointers and short/failed reads refuse.
 * At most 112 reader calls, each <=64 bytes. Null events skip handle reads;
 * reference counts are excluded. Out-of-image tables are never dereferenced.
 * Equality can miss intervening changes and reuse; it is not atomicity.
 */
int snow_animation_queue_observe(SnowEntryRead,void *,uint64_t component,
    uint64_t owner,uint64_t image_base,uint64_t image_size,SnowAnimationQueueSnapshot *);
#endif
