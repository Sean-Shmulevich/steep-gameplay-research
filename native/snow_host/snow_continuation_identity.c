#include "snow_continuation_identity.h"
#include <string.h>
static uint64_t hash(const unsigned char *p,unsigned n){
    uint64_t h=UINT64_C(14695981039346656037);
    for(unsigned i=0;i<n;i++)h=(h^p[i])*UINT64_C(1099511628211);
    return h;
}
int snow_continuation_matches(const SnowContinuationSample *s,uint64_t prefix,uint64_t tail){
    if(!s || s->entry<0x10000 || s->candidate<0x10000 || s->expected_handler<0x10000 ||
       s->entry>UINT64_C(0x7fffffffffff)-64 || s->candidate>UINT64_C(0x7fffffffffff)-64 ||
       s->expected_handler>UINT64_C(0x7fffffffffff))return 0;
    if(s->entry_bytes[0]!=0xe9 || s->candidate_bytes[8]!=0xe9 ||
       s->candidate_bytes[21]!=0xff || s->candidate_bytes[22]!=0x25 ||
       hash(s->candidate_bytes,8)!=prefix || hash(s->entry_bytes+8,24)!=tail)return 0;
    int32_t entry_delta,return_delta,slot_delta;uint64_t handler;
    memcpy(&entry_delta,s->entry_bytes+1,4);memcpy(&return_delta,s->candidate_bytes+9,4);
    memcpy(&slot_delta,s->candidate_bytes+23,4);memcpy(&handler,s->candidate_bytes+27,8);
    return s->entry+5+(intptr_t)entry_delta==s->candidate+21 &&
        s->candidate+13+(intptr_t)return_delta==s->entry+8 &&
        slot_delta==0 && handler==s->expected_handler;
}
