#include "snow_step_contract.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    assert(snow_step_release_stable(41,42,42,1));
    assert(snow_step_release_stable(9806,9814,9814,1)); /* recorded request gap */
    assert(!snow_step_release_stable(41,41,41,1));
    assert(!snow_step_release_stable(41,42,43,1));
    assert(!snow_step_release_stable(41,42,42,0));
    assert(snow_step_release_stable(UINT32_MAX,0,0,1));
    /* A gap does not establish multiple executions, nor rule them out. */
    assert(snow_step_release_stable(UINT32_MAX,1,1,1));
    puts("PASS: request token stability does not assert execution count");
    return 0;
}
