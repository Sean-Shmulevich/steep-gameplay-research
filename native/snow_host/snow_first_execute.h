#ifndef SNOW_FIRST_EXECUTE_H
#define SNOW_FIRST_EXECUTE_H
#include <windows.h>
#include <stdint.h>
/* Authored diagnostic, not recovered engine behavior.
 * One arm per process. Caller retains the entire dedicated RX private/image page
 * until process exit, excludes protection changes, and serializes arm/cancel.
 * The first execution ANYWHERE on the page wins, before the instruction runs.
 * Observer module is pinned. No unload support or instruction/register edits.
 * Cancel/read are controller operations; never invoke them from a fault handler.
 * A process watchdog remains necessary: this instrumentation can stall/fail.
 */
typedef struct {
    uintptr_t fault_address, instruction;
    uint64_t tick;
    DWORD thread;
    CONTEXT context;
    uint32_t stack_valid;
    unsigned char stack[128]; /* Sequential snapshot at RSP, not an unwound stack. */
} SnowFirstExecuteRecord;
/* Optional before Arm. Callback uses VirtualProtect-style success/old protection
 * and sets GetLastError on failure. It must work in a VEH without waiting on game
 * jobs or allocating. Its module is pinned; caller retains context and every
 * indirect dependency through process exit. Context extent/lifetime is not
 * inferred by the observer. Callback module and context must not overlap the
 * watched page. Default backend remains VirtualProtect. */
typedef BOOL (*SnowExecuteProtect)(void *context,void *address,SIZE_T size,DWORD protection,DWORD *old);
int snow_first_execute_backend(SnowExecuteProtect protect,void *context);
int snow_first_execute_arm(void *address);
int snow_first_execute_cancel(void); /* Retry if another thread is restoring. */
int snow_first_execute_read(SnowFirstExecuteRecord *out);
/* Controller-only diagnostics after Arm returns: no concurrent reconfiguration.
 * stage: 0 unused, 1 query/eligibility, 2 observer/backend overlap, 3 module pin,
 * 4 handler registration, 5 protection change, 6 armed. Error is an OS failure
 * code only for stages 3..5; zero elsewhere is not proof of success. */
void snow_first_execute_arm_diagnostic(unsigned *stage,DWORD *error);
#endif
