#include "snow_motion_observation.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned char memory[0x10000];
static int reads,fail_at,mutate;
static void put(uint64_t a,uint64_t v,int n) {for(int i=0;i<n;i++) memory[a+i]=(unsigned char)(v>>(i*8));}
static int read_mem(void *ctx,uint64_t a,void *out,size_t n) {
    (void)ctx;reads++;
    if(mutate && reads==10) put(0x2010+0x384,99,4);
    if(reads==fail_at || a>sizeof memory || n>sizeof memory-a) return 0;
    memcpy(out,memory+a,n);return 1;
}
static void setup(void) {
    memset(memory,0,sizeof memory);reads=fail_at=mutate=0;
    put(0x1000,0x9000,8);put(0x2050,0x1000,8);
    put(0x2010+0x10,0x6000,8);put(0x2010+0x18,0x7777,8);
    put(0x6018,4,4);put(0x601c,5,4);put(0x6020,0x7000,8);
    put(0x7018,6,4);put(0x701c,9,4);put(0x7020,0x8000,8);
    put(0x2010+0x384,17,4);put(0x2010+0x388,23,4);
    put(0x2010+0x47d,0x000001,3); /* combined stale: 1, first 0, second 0 */
    put(0x2010+0x160,0x7fc01234,4);put(0x2010+0x700,0x80000000,4);
}
static int zero(const SnowMotionObservation *s) {
    unsigned char b[sizeof *s];memset(b,0,sizeof b);return !memcmp(s,b,sizeof b);
}
int main(void) {
    SnowMotionObservation s;
    setup();assert(snow_motion_observe(read_mem,0,0x1000,0x9000,&s));assert(reads==18);
    assert(s.motion==0x2010 && s.state_observed && s.child_observed && s.child_mode==6);
    assert(s.nonzero_counts[0]==17 && s.nonzero_counts[1]==23);
    assert(s.ingested[0]==0x7fc01234 && s.baselines[8]==0x80000000);
    assert(s.latches[0]==1 && s.latches[1]==0 && s.latches[2]==0);
    assert(s.pending==0x7777); /* pending pointer is never followed */
    for(int i=1;i<=18;i++) {setup();fail_at=i;memset(&s,255,sizeof s);assert(!snow_motion_observe(read_mem,0,0x1000,0x9000,&s));assert(zero(&s));}
    setup();mutate=1;assert(!snow_motion_observe(read_mem,0,0x1000,0x9000,&s));assert(zero(&s));
    setup();put(0x2050,0x1111,8);assert(!snow_motion_observe(read_mem,0,0x1000,0x9000,&s));assert(zero(&s));
    setup();assert(!snow_motion_observe(read_mem,0,0x1000,0x9999,&s));assert(reads==1);
    setup();put(0x2018,2,4);put(0x2020,UINT64_MAX,8);assert(snow_motion_observe(read_mem,0,0x1000,0x9000,&s));assert(reads==14 && !s.state_observed);
    setup();put(0x6018,1,4);put(0x6020,UINT64_MAX,8);assert(snow_motion_observe(read_mem,0,0x1000,0x9000,&s));assert(reads==16 && !s.child_observed);
    setup();put(0x6020,UINT64_MAX-8,8);assert(!snow_motion_observe(read_mem,0,0x1000,0x9000,&s));assert(zero(&s));
    setup();assert(!snow_motion_observe(read_mem,0,0x1001,0x9000,&s));assert(reads==0);
    puts("PASS: bounded motion observation, failure matrix and branch exclusions");return 0;
}
