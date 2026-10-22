#include "snow_batch_frame.h"
#include <string.h>
typedef struct {
    uint64_t caller,owner,ordinal,world,counter;
    uint32_t count,elapsed,consumed;
} Sample;
static int read_at(SnowEntryRead read,void *ctx,uint64_t base,uint64_t off,void *out,size_t size) {
    if(!base || off>UINT64_MAX-base || size>UINT64_MAX-(base+off)) return 0;
    return read(ctx,base+off,out,size);
}
static int sample(SnowEntryRead read,void *ctx,uint64_t job,uint64_t expected_return,
                  uint64_t world,uint32_t elapsed,uint32_t consumed,Sample *s) {
    memset(s,0,sizeof *s);
    /* Reject wrong caller before following its saved-register interpretation. */
    if(!read_at(read,ctx,job,0x1b58,&s->caller,8) || s->caller!=expected_return ||
       !read_at(read,ctx,job,0x1b60,&s->owner,8) ||
       !read_at(read,ctx,job,0x1b70,&s->ordinal,8) ||
       !read_at(read,ctx,s->owner,0,&s->world,8) || s->world!=world ||
       !read_at(read,ctx,s->owner,0x1390,&s->count,4) || s->ordinal>=s->count ||
       !read_at(read,ctx,s->owner,0x1394,&s->elapsed,4) || s->elapsed!=elapsed ||
       !read_at(read,ctx,s->owner,0x136c,&s->consumed,4) || s->consumed!=consumed ||
       !read_at(read,ctx,s->world,0x20,&s->counter,8)) return 0;
    return 1;
}
int snow_batch_frame(SnowEntryRead read,void *ctx,uint64_t job,uint64_t expected_return,
                     uint64_t expected_world,uint32_t elapsed_bits,
                     uint32_t consumed_bits,SnowBatchFrame *out) {
    Sample a,b;
    if(!out) return 0;
    memset(out,0,sizeof *out);
    if(!read || !job || !expected_return || !expected_world ||
       !sample(read,ctx,job,expected_return,expected_world,elapsed_bits,consumed_bits,&a) ||
       !sample(read,ctx,job,expected_return,expected_world,elapsed_bits,consumed_bits,&b) ||
       memcmp(&a,&b,sizeof a)) return 0;
    out->timing_owner=a.owner;out->world=a.world;out->outer_completion_counter=a.counter;
    out->ordinal=(uint32_t)a.ordinal;out->selected_count=a.count;
    out->elapsed_bits=a.elapsed;out->consumed_bits=a.consumed;
    return 1;
}
