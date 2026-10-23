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
#define SNOW_FIRST_WRITE_WINDOWS 3
#define SNOW_FIRST_WRITE_WINDOW_BYTES 128
typedef enum { SNOW_WRITE_RSP=1, SNOW_WRITE_RBP=2, SNOW_WRITE_RBX=3, SNOW_WRITE_FAULT=4 } SnowWriteSource;
typedef struct { SnowWriteSource source; int32_t offset; uint32_t size; } SnowWriteWindowSpec;
typedef struct {
    uintptr_t address;
    uint32_t size, valid;
    unsigned char bytes[SNOW_FIRST_WRITE_WINDOW_BYTES];
} SnowWriteWindow;
typedef struct {
    uintptr_t fault_address, instruction;
    uint64_t tick;
    DWORD thread;
    CONTEXT context;
    uint32_t window_count;
    SnowWriteWindow windows[SNOW_FIRST_WRITE_WINDOWS];
} SnowFirstWriteRecord;
/* Optional before Arm; at most 3 windows of 128 bytes, offsets within +/-4096.
 * Sequential bounded reads while faulting thread is stopped, not atomic against
 * other threads. Failed/guarded/unreadable ranges are invalid and zero-filled.
 * All consumers must rebuild with this header; no stable binary record ABI.
 */
int snow_first_write_windows(const SnowWriteWindowSpec *specs,uint32_t count);
int snow_first_write_arm(void *address);
int snow_first_write_cancel(void);
int snow_first_write_read(SnowFirstWriteRecord *out);
#endif
