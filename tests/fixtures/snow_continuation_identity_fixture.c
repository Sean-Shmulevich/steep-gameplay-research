#include "snow_continuation_identity.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static uint64_t hash(const unsigned char *p,unsigned n){
    uint64_t h=UINT64_C(14695981039346656037);for(unsigned i=0;i<n;i++)h=(h^p[i])*UINT64_C(1099511628211);return h;
}
int main(void){
    SnowContinuationSample good={0};good.entry=0x100000;good.candidate=0x200000;good.expected_handler=0x300000;
    for(unsigned i=0;i<8;i++)good.candidate_bytes[i]=(unsigned char)(i+1);
    for(unsigned i=8;i<32;i++)good.entry_bytes[i]=(unsigned char)(i+7);
    good.entry_bytes[0]=0xe9;good.candidate_bytes[8]=0xe9;good.candidate_bytes[21]=0xff;good.candidate_bytes[22]=0x25;
    int32_t d=(int32_t)(good.candidate+21-good.entry-5);memcpy(good.entry_bytes+1,&d,4);
    d=(int32_t)(good.entry+8-good.candidate-13);memcpy(good.candidate_bytes+9,&d,4);
    uint64_t h=good.expected_handler;memcpy(good.candidate_bytes+27,&h,8);
    uint64_t prefix=hash(good.candidate_bytes,8),tail=hash(good.entry_bytes+8,24);
    assert(snow_continuation_matches(&good,prefix,tail));assert(!snow_continuation_matches(NULL,prefix,tail));
    unsigned offsets[]={0,1,8,9,21,22,23,27};
    for(unsigned i=0;i<sizeof offsets/sizeof offsets[0];i++){
        SnowContinuationSample s=good;s.candidate_bytes[offsets[i]]^=1;assert(!snow_continuation_matches(&s,prefix,tail));
    }
    for(unsigned i=0;i<3;i++){
        SnowContinuationSample s=good;s.entry_bytes[(unsigned[]){0,1,8}[i]]^=1;assert(!snow_continuation_matches(&s,prefix,tail));
    }
    SnowContinuationSample s=good;s.entry=0;assert(!snow_continuation_matches(&s,prefix,tail));
    s=good;s.candidate=UINTPTR_MAX;assert(!snow_continuation_matches(&s,prefix,tail));
    s=good;s.expected_handler++;assert(!snow_continuation_matches(&s,prefix,tail));
    assert(!snow_continuation_matches(&good,prefix^1,tail));assert(!snow_continuation_matches(&good,prefix,tail^1));
    puts("18 continuation identity cases passed");return 0;
}
