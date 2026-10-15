/* Simulated engine for testing the host without the game. SYNTHETIC: it
 * models only the stop-mode routing that the host relies on. A request runs
 * every ~16 ms; Step runs when the mode group is ordinary, the paused job runs
 * otherwise, and EndFrame always runs. A simulated player moves 0.25 units along
 * x per Step (velocity 15 units/s), so a held simulation keeps it still. It is not
 * a model of the engine. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "snow_adapter.h"

static struct { volatile LONG group; volatile LONG step, paused, end_frame; } sim;
static LONG running;
static volatile LONG player_steps;   /* Step executions since bind, read for the position */
static int player_mode;              /* 0 none, 1 bound, 2 bound and expires after 5 reads */
static int player_reads;

static DWORD WINAPI requests(LPVOID unused) {
    (void)unused;
    for (LONG frame = 1;; frame++) {
        uint32_t g = (uint32_t)sim.group;          /* read once per request, like CheckEngineStop */
        if (SNOW_GROUP_ORDINARY(g)) { InterlockedExchange(&sim.step, frame); InterlockedIncrement(&player_steps); }
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

static int player_bind(const char *handle, char *why, size_t n) {
    if (!strcmp(handle, "fixture-player")) player_mode = 1;
    else if (!strcmp(handle, "fixture-player-expiring")) player_mode = 2;
    else { snprintf(why, n, "unknown fixture handle"); return 1; }
    player_reads = 0;
    InterlockedExchange(&player_steps, 0);
    return 0;
}
static int player_read(SnowPlayerRaw *out, char *why, size_t n) {
    if (!player_mode) { snprintf(why, n, "no player"); return 1; }
    if (player_mode == 2 && ++player_reads > 5) { player_mode = 0; snprintf(why, n, "fixture player expired"); return 2; }
    memset(out, 0, sizeof *out);
    out->transform[0] = out->transform[5] = out->transform[10] = out->transform[15] = 1.0f;
    out->transform[12] = 0.25f * (float)player_steps;
    out->transform[13] = 100.0f;
    out->linear_velocity[0] = 15.0f;
    out->angular_velocity[1] = 0.5f;
    return 0;
}

const SnowAdapter snow_adapter = {"fixture-simulated", bind, read, cas_group, enter, leave, player_bind, player_read};
