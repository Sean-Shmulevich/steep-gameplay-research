/* Game adapter boundary for the Snow mod host.
 *
 * The host core never contains game addresses. A build links exactly one
 * adapter: the private, build-specific game adapter or the simulated fixture
 * adapter. Every adapter call happens on the host executor thread.
 */
#ifndef SNOW_ADAPTER_H
#define SNOW_ADAPTER_H
#include <stddef.h>
#include <stdint.h>

/* Mode group bytes in memory order: neighbor, mode, companion, request_arg. */
#define SNOW_GROUP_BYTE(g, i) (((g) >> (8 * (i))) & 0xffu)
#define SNOW_GROUP_HELD(g) (SNOW_GROUP_BYTE(g, 1) == 1 && SNOW_GROUP_BYTE(g, 2) == 1)
#define SNOW_GROUP_ORDINARY(g) (SNOW_GROUP_BYTE(g, 1) == 0 && SNOW_GROUP_BYTE(g, 2) == 0)

typedef struct SnowCounters {
    uint64_t owner;      /* opaque identity of the current engine owner; never an API field */
    uint32_t group;      /* stop-mode group */
    uint32_t step;       /* world Step job, last-run request */
    uint32_t paused;     /* UpdateWhileEngineIsPaused job, last-run request */
    uint32_t end_frame;  /* EndFrame job, last-run request */
} SnowCounters;

typedef struct SnowAdapter {
    const char *name;
    /* Verify process/image identity once. Returns 0 or writes a reason. */
    int (*bind)(char *why, size_t n);
    /* Fresh owner lookup and counter read. Returns 0 or writes a reason. */
    int (*read)(SnowCounters *c, char *why, size_t n);
    /* Atomic compare-and-swap of the mode group only. *seen receives the prior value. */
    int (*cas_group)(uint64_t owner, uint32_t expect, uint32_t want, uint32_t *seen);
    /* The engine's own stop-mode setter (request argument 1) and clear routine. */
    int (*enter)(void);
    int (*leave)(void);
} SnowAdapter;

extern const SnowAdapter snow_adapter;
#endif
