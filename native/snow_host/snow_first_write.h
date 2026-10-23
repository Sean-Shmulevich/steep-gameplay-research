#ifndef SNOW_FIRST_WRITE_H
#define SNOW_FIRST_WRITE_H
#include <windows.h>
#include <stdint.h>
/* Authored one-shot page observer, not recovered game code.
 * Caller retains an entire committed READWRITE data page or WRITECOPY image page through process exit
 * and excludes all other protection changes. Never use a heap allocator page.
 * The first write ANYWHERE on that page wins; the instruction has not completed.
 * Arm once, on one controller thread. Cancel may need retry while handling.
 * Handler/code stay registered and pinned until process exit. No unload API.
 * Foreign faults are forwarded. No instruction bytes/registers are modified.
 */
typedef struct {
    uintptr_t fault_address, instruction;
    uint64_t tick;
    DWORD thread;
    CONTEXT context;
} SnowFirstWriteRecord;
int snow_first_write_arm(void *address);
int snow_first_write_cancel(void);
int snow_first_write_read(SnowFirstWriteRecord *out);
#endif
