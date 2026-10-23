#ifndef SNOW_FIRST_EXECUTE_H
#define SNOW_FIRST_EXECUTE_H
#include <windows.h>
#include <stdint.h>
/* Authored diagnostic, not recovered engine behavior.
 * One arm per process. Caller retains the entire dedicated RX private/image page
 * until process exit, excludes protection changes, and serializes arm/cancel.
 * The first matching execute fault touching the page wins, before the instruction
 * runs. Its RIP can start up to 14 bytes before the page for a spanning instruction.
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
/* Optional caller-owned RW storage, retained until process exit. Individual
 * counters are atomic; the collection is not an atomic snapshot. A file mapping
 * lets diagnostics survive process exit without performing file IO in the VEH.
 * phase: 0 no winning fault, 1 winner, 2 stack sampled, 3 restoring,
 * 4 capture published, 5 restoration failed. Not an engine state/API. */
#define SNOW_EXECUTE_TRACE_CAPACITY 8
typedef struct {
    volatile LONG64 published;
    uint64_t code, flags, parameter_count, reason, operation, address, instruction;
} SnowExecuteExceptionTrace;
typedef struct {
    volatile LONG version, handler_entries, matched_entries, phase, restore_error, capacity;
    SnowExecuteExceptionTrace exceptions[SNOW_EXECUTE_TRACE_CAPACITY];
} SnowFirstExecuteTrace;
/* Pure classification; no reads through game pointers. Reasons: 0 match,
 * 1 missing exception/context, 2 not AV, 3 insufficient parameters,
 * 4 noncontinuable, 5 not execution access, 6 fault outside page,
 * 7 RIP outside the page and its 14-byte instruction-start allowance.
 * The first eight handler entries retain metadata, not just matching faults. */
unsigned snow_first_execute_classify(const EXCEPTION_POINTERS *exception,uintptr_t page,SIZE_T size);
int snow_first_execute_trace(SnowFirstExecuteTrace *trace);
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
