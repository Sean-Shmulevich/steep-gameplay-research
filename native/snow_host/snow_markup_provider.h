#ifndef SNOW_MARKUP_PROVIDER_H
#define SNOW_MARKUP_PROVIDER_H
#include "snow_entry_attribution.h"
#define SNOW_MARKUP_RECORD_LIMIT 8
/* Private observation layout, not a game object or stable wire ABI. */
typedef struct { uint32_t key,scalar54_bits,start_bits,end_bits;uint8_t flags; } SnowMarkupScalarRecord;
typedef struct {
    uint64_t component,controller,markup,query_owner,interface,attachment,graph;
    uint64_t header,data,packed_header,notification_data;
    uint32_t record_count,notification_count;
    SnowMarkupScalarRecord records[SNOW_MARKUP_RECORD_LIMIT];
} SnowMarkupUpdateSnapshot;
/* Caller establishes fresh component provenance and verified process/image.
 * Two identical sequential samples required. No pin, atomicity, game calls,
 * allocation or writes. Output zeroed on rejection. Reader returns exactly 1.
 * Each read <=17 bytes. At most 56 reads; records over eight reject.
 */
int snow_markup_provider_observe(SnowEntryRead,void *,uint64_t component,
    uint64_t image_base,uint64_t image_size,SnowMarkupUpdateSnapshot *);
#endif
