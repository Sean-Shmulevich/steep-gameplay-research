/* Simulated engine for testing the host without the game. SYNTHETIC: it
 * models only the stop-mode routing that the host relies on. A request runs
 * every ~16 ms; Step runs when the mode group is ordinary, the paused job runs
 * otherwise, and EndFrame always runs. It is not a model of the engine. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include "snow_adapter.h"

static struct { volatile LONG group; volatile LONG step, paused, end_frame; } sim;
static LONG running;

static DWORD WINAPI requests(LPVOID unused) {
    (void)unused;
    for (LONG frame = 1;; frame++) {
        uint32_t g = (uint32_t)sim.group;          /* read once per request, like CheckEngineStop */
        if (SNOW_GROUP_ORDINARY(g)) InterlockedExchange(&sim.step, frame);
        else InterlockedExchange(&sim.paused, frame);
        InterlockedExchange(&sim.end_frame, frame);
        Sleep(16);
    }
    return 0;
}

static int bind(char *why, size_t n) {
    if (InterlockedCompareExchange(&running, 1, 0) == 0) {
        sim.group = 0x01000000; /* request_arg byte set, as in observed baselines */
        HANDLE t = CreateThread(NULL, 0, requests, NULL, 0, NULL);
        if (!t) { snprintf(why, n, "simulator thread failed"); return 1; }
        CloseHandle(t);
    }
    return 0;
}
static int read(SnowCounters *c, char *why, size_t n) {
    (void)why; (void)n;
    c->owner = (uint64_t)(uintptr_t)&sim;
    c->group = (uint32_t)sim.group; c->step = (uint32_t)sim.step;
    c->paused = (uint32_t)sim.paused; c->end_frame = (uint32_t)sim.end_frame;
    return 0;
}
static int cas_group(uint64_t owner, uint32_t expect, uint32_t want, uint32_t *seen) {
    if (owner != (uint64_t)(uintptr_t)&sim) return 1;
    *seen = (uint32_t)InterlockedCompareExchange(&sim.group, (LONG)want, (LONG)expect);
    return *seen != expect;
}
static int enter(void) { InterlockedExchange(&sim.group, (LONG)(((uint32_t)sim.group & 0xffu) | 0x01010100u)); return 0; }
static int leave(void) { InterlockedExchange(&sim.group, (LONG)((uint32_t)sim.group & 0xff000000u)); return 0; }

const SnowAdapter snow_adapter = {"fixture-simulated", bind, read, cas_group, enter, leave};
