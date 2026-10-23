#include "snow_finite_diagnostic.h"
#include <assert.h>
int main(void) {
    float values[16] = {0}; char why[128], expected[128];
    uint32_t bad[] = {0x7f800000u, 0xff800000u, 0x7fc01234u, 0x7f801234u};
    for (size_t i = 0; i < 16; ++i) {
        for (size_t j = 0; j < sizeof bad / sizeof bad[0]; ++j) {
            memcpy(values+i, bad+j, 4);
            assert(snow_nonfinite_field(values,16,"transform",why,sizeof why));
            snprintf(expected,sizeof expected,"nonfinite transform[%zu] bits=%08x",i,(unsigned)bad[j]);
            assert(!strcmp(why,expected));
            values[i]=0;
        }
    }
    uint32_t finite[] = {0,0x80000000u,1,0x7f7fffffu,0xff7fffffu};
    for(size_t i=0;i<sizeof finite/sizeof finite[0];++i) {
        memcpy(values,finite+i,4);
        assert(!snow_nonfinite_field(values,16,"transform",why,sizeof why));
    }
    memcpy(values,bad,4);
    char tiny[2]={'X','X'};
    assert(snow_nonfinite_field(values,16,"transform",tiny,sizeof tiny));
    assert(tiny[1]==0);
    puts("PASS: finite guard and exact diagnostic bits");
    return 0;
}
