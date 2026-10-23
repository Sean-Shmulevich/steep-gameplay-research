/* Independently authored, build-specific Steep adapter for the Snow mod host.
 * Analyzed memory-image SHA-256:
 * 32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2
 * Fixed addresses and short signature checks are build-specific evidence,
 * not a complete executable hash check or a compatibility guarantee.
 * Published with user authorization; no game executable or asset bytes included.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include "snow_adapter.h"
#include "snow_finite_diagnostic.h"
#include "snow_animation_reader.h"
#include "steep_probe_binding.h"

#define IMAGE_BASE 0x140000000ull
#define OWNER_SLOT 0x14312cfe8ull
#define SETTER 0x14069d110ull
#define CLEAR 0x14069a190ull
#define GROUP 0x40
#define STEP_LAST (0x3ab0 + 0x58)
#define PAUSED_LAST (0x2440 + 0x58)
#define END_FRAME_LAST (0x4dc8 + 0x58)
#define OWNER_SPAN (END_FRAME_LAST + 4)

static const unsigned char setter_sig[] = {0x48, 0x8b, 0x05, 0xd1, 0xfe, 0xa8, 0x02};
static const unsigned char clear_sig[] = {0x48, 0x83, 0xec, 0x28, 0x48, 0x8b, 0x05};
typedef void (*NativeRoutine)(uintptr_t);
static uint64_t checked_owner;

static DWORD last_state, last_protect;
static int readable(uint64_t a, size_t n, int need_write) {
    MEMORY_BASIC_INFORMATION m;
    last_state = last_protect = 0;
    if (!VirtualQuery((LPCVOID)(uintptr_t)a, &m, sizeof m)) return 0;
    last_state = m.State; last_protect = m.Protect;
    if (m.State != MEM_COMMIT || (m.Protect & (PAGE_GUARD | PAGE_NOACCESS))) return 0;
    /* Image data sections may be copy-on-write; a write there still lands in this process. */
    DWORD writable = PAGE_READWRITE | PAGE_EXECUTE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_WRITECOPY;
    DWORD ok = need_write ? writable : (writable | PAGE_READONLY | PAGE_EXECUTE_READ);
    if (!(m.Protect & ok)) return 0;
    return a + n <= (uint64_t)(uintptr_t)m.BaseAddress + m.RegionSize;
}

static int bind(char *why, size_t n) {
    WCHAR path[MAX_PATH]; DWORD k = GetModuleFileNameW(NULL, path, MAX_PATH);
    const WCHAR *base = wcsrchr(path, L'\\');
    if (!k || _wcsicmp(base ? base + 1 : path, L"steep.exe")) { snprintf(why, n, "process is not steep.exe"); return 1; }
    if ((uint64_t)(uintptr_t)GetModuleHandleW(NULL) != IMAGE_BASE) { snprintf(why, n, "unexpected image base"); return 1; }
    if (!readable(SETTER, sizeof setter_sig, 0) || memcmp((void *)(uintptr_t)SETTER, setter_sig, sizeof setter_sig) ||
        !readable(CLEAR, sizeof clear_sig, 0) || memcmp((void *)(uintptr_t)CLEAR, clear_sig, sizeof clear_sig)) {
        snprintf(why, n, "stop-mode routines differ from the analyzed build"); return 1;
    }
    if (!readable(OWNER_SLOT, 8, 0)) { snprintf(why, n, "owner slot unreadable (state 0x%lx, protect 0x%lx)", last_state, last_protect); return 1; }
    return 0;
}

static int read(SnowCounters *c, char *why, size_t n) {
    uint64_t owner = *(volatile uint64_t *)(uintptr_t)OWNER_SLOT;
    if (owner < 0x10000 || owner >= 0x800000000000ull || (owner & 3)) { snprintf(why, n, "invalid engine owner"); return 1; }
    if (owner != checked_owner) {
        if (!readable(owner, OWNER_SPAN, 1)) { snprintf(why, n, "engine owner region not accessible (state 0x%lx, protect 0x%lx)", last_state, last_protect); return 1; }
        checked_owner = owner;
    }
    volatile unsigned char *o = (volatile unsigned char *)(uintptr_t)owner;
    c->owner = owner;
    c->group = *(volatile uint32_t *)(o + GROUP);
    c->step = *(volatile uint32_t *)(o + STEP_LAST);
    c->paused = *(volatile uint32_t *)(o + PAUSED_LAST);
    c->end_frame = *(volatile uint32_t *)(o + END_FRAME_LAST);
    return 0;
}

static int cas_group(uint64_t owner, uint32_t expect, uint32_t want, uint32_t *seen) {
    if (owner != *(volatile uint64_t *)(uintptr_t)OWNER_SLOT || owner != checked_owner) { *seen = 0; return 1; }
    *seen = (uint32_t)InterlockedCompareExchange((volatile LONG *)(uintptr_t)(owner + GROUP), (LONG)want, (LONG)expect);
    return *seen != expect;
}

static int enter(void) { ((NativeRoutine)(uintptr_t)SETTER)(1); return 0; }
static int leave(void) { ((NativeRoutine)(uintptr_t)CLEAR)(0); return 0; }

/* ---- player body (run36-validated chain; handle = actor pointer from the external acquisition) ----
 * actor: vtable 0x141e7a350, +0x1050 == actor, entity = +0x10 (nonnull), world = entity+0x60 (pinned at bind)
 * runtime = actor+0x168: vtable 0x142918ea8, +0x6f0 == actor; body = runtime+0x6e8 (refreshed every read)
 * body: transform 16 floats at +0x40 (translation +0x70), linear velocity +0x1a0, angular +0x1ac. */
#define ACTOR_VT 0x141e7a350ull
#define RUNTIME_VT 0x142918ea8ull
static uint64_t p_actor, p_entity, p_world, last_world;
static void diag(const char *tag);

static int plausible(uint64_t a) { return a >= 0x10000 && a < 0x800000000000ull && !(a & 7); }
static uint64_t q(uint64_t a) { return *(volatile uint64_t *)(uintptr_t)a; }

/* Returns body pointer or 0; writes a reason. */
static uint64_t player_links(char *why, size_t n) {
    uint64_t a = p_actor;
    if (!readable(a, 0x1058, 0)) { snprintf(why, n, "actor unreadable"); return 0; }
    if (q(a) != ACTOR_VT || q(a + 0x1050) != a) { snprintf(why, n, "actor identity changed"); return 0; }
    uint64_t e = q(a + 0x10);
    if (!plausible(e) || !readable(e + 0x60, 8, 0)) { snprintf(why, n, "entity invalid"); return 0; }
    if (p_entity && (e != p_entity || q(e + 0x60) != p_world)) { snprintf(why, n, "entity or world changed"); return 0; }
    uint64_t r = q(a + 0x168);
    if (!plausible(r) || !readable(r, 0x6f8, 0) || q(r) != RUNTIME_VT || q(r + 0x6f0) != a) { snprintf(why, n, "runtime link invalid"); return 0; }
    uint64_t body = q(r + 0x6e8);
    if (!plausible(body) || !readable(body + 0x40, 0x178, 0)) { snprintf(why, n, "body invalid"); return 0; }
    return body;
}

static int player_bind(const char *handle, char *why, size_t n) {
    char *end; unsigned long long a = strtoull(handle, &end, 16);
    p_actor = p_entity = p_world = 0;
    if (*end || !plausible(a)) { snprintf(why, n, "handle must be a hex actor pointer"); return 1; }
    p_actor = a;
    if (!player_links(why, n)) { p_actor = 0; return 1; }
    p_entity = q(a + 0x10); p_world = q(p_entity + 0x60);
    last_world = p_world;
    return 0;
}

static int player_read(SnowPlayerRaw *out, char *why, size_t n) {
    if (!p_actor) { snprintf(why, n, "no player bound"); return 1; }
    uint64_t body = player_links(why, n);
    if (!body) { p_actor = 0; return 2; }
    memcpy(out->transform, (const void *)(uintptr_t)(body + 0x40), sizeof out->transform);
    memcpy(out->linear_velocity, (const void *)(uintptr_t)(body + 0x1a0), sizeof out->linear_velocity);
    memcpy(out->angular_velocity, (const void *)(uintptr_t)(body + 0x1ac), sizeof out->angular_velocity);
    /* Backend descriptor [body+0x30] (from 0x1418aa520 / 0x1418b8380): [[desc+0x20]+0x20] is the simulation
     * world (null = not in a world). Live player-8: clear exactly while the body was frozen after a crash and
     * during respawn staging. (+0x52 bit0 and +0x53 nibble stayed 0 throughout; not exported.) */
    out->flags = 0;
    uint64_t desc = q(body + 0x30);
    if (plausible(desc) && readable(desc + 0x20, 0x34, 0)) {
        uint64_t w1 = q(desc + 0x20);
        int in_world = plausible(w1) && readable(w1 + 0x20, 8, 0) && q(w1 + 0x20) != 0;
        out->flags = 0x1u | (in_world ? 0x2u : 0);
    }
    if (player_links(why, n) != body) { p_actor = 0; return 2; }   /* bracket: links unchanged across the copy */
    if (snow_nonfinite_field(out->transform, 16, "transform", why, n)) return 1;
    for (int k = 0; k < 3; k++)
        if (snow_nonfinite_field(out->linear_velocity + k, 1, k == 0 ? "linear_velocity.x" : k == 1 ? "linear_velocity.y" : "linear_velocity.z", why, n) ||
            snow_nonfinite_field(out->angular_velocity + k, 1, k == 0 ? "angular_velocity.x" : k == 1 ? "angular_velocity.y" : "angular_velocity.z", why, n)) return 1;
    diag("read");
    return 0;
}

/* ---- velocity assignment through the engine's own routine ----
 * 0x141397ba0(actor, const float4 *v (16-byte aligned), bool legs): thunk reads actor+0x168 and tails to
 * 0x141404910, which locks runtime+0x1588, sets main-body linear velocity (0x1418aa520), zeroes angular
 * (0x1418aa360), refreshes motion (0x14140a880), resets speed history and copies v into runtime+0xaa0/+0xa90.
 * Game callers: 0x140530970, 0x14053e6b8, 0x14056d850 (the last passes r8=0, as we do). */
#define SET_VEL 0x141397ba0ull
#define SET_VEL_BODY 0x141404910ull
static const unsigned char set_vel_sig[] = {0x48, 0x8b, 0x89, 0x68, 0x01, 0x00, 0x00, 0x48, 0x85, 0xc9, 0x0f, 0x85, 0x60, 0xcd, 0x06, 0x00};
static const unsigned char set_vel_body_sig[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x6c, 0x24, 0x10, 0x48, 0x89, 0x74, 0x24, 0x18,
                                                 0x48, 0x89, 0x7c, 0x24, 0x20, 0x41, 0x56, 0x48, 0x83, 0xec, 0x70, 0x48, 0x8b, 0x81, 0x88, 0x15, 0x00};
typedef void (*SetVelocity)(uintptr_t actor, const float *v, unsigned char legs);

/* PRIVATE experiment switches: steep_adapter.ini next to the host DLL, re-read on each use.
 *   legs=0|1   third argument of the velocity routine (default 1: also re-poses the rider body)
 *   diag=0|1   append main/rider body velocity and actor+0x1d0/+0x1e0 to steep_adapter_diag.txt on every read/set */
static WCHAR ini_path[MAX_PATH], diag_path[MAX_PATH];
static int ini_int(const WCHAR *key, int dflt) {
    if (!ini_path[0]) {
        HMODULE self = NULL;
        GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCWSTR)(void *)ini_int, &self);
        DWORD k = GetModuleFileNameW(self, ini_path, MAX_PATH);
        while (k && ini_path[k - 1] != L'\\') k--;
        ini_path[k] = 0;
        wcscpy(diag_path, ini_path);
        wcscat(ini_path, L"steep_adapter.ini"); wcscat(diag_path, L"steep_adapter_diag.txt");
    }
    return (int)GetPrivateProfileIntW(L"adapter", key, dflt, ini_path);
}
static void diag(const char *tag) {
    if (!ini_int(L"diag", 0) || !p_actor) return;
    uint64_t r = q(p_actor + 0x168), body = q(r + 0x6e8), rider = readable(r + 0xb90, 8, 0) ? q(r + 0xb90) : 0;
    const float *mv = (const float *)(uintptr_t)(body + 0x1a0);
    float rv[3] = {0, 0, 0};
    if (plausible(rider) && readable(rider + 0x1a0, 12, 0)) memcpy(rv, (const void *)(uintptr_t)(rider + 0x1a0), 12);
    const float *d0 = (const float *)(uintptr_t)(p_actor + 0x1d0), *e0 = (const float *)(uintptr_t)(p_actor + 0x1e0);
    FILE *f = _wfopen(diag_path, L"a");
    if (!f) return;
    fprintf(f, "%s main=(%.4f,%.4f,%.4f) rider%s=(%.4f,%.4f,%.4f) a1d0=(%.4f,%.4f,%.4f) a1e0=(%.4f,%.4f,%.4f)\n", tag,
            mv[0], mv[1], mv[2], plausible(rider) ? "" : "(none)", rv[0], rv[1], rv[2], d0[0], d0[1], d0[2], e0[0], e0[1], e0[2]);
    fclose(f);
}

static int player_set_velocity(const float v[3], char *why, size_t n) {
    if (!p_actor) { snprintf(why, n, "no player bound"); return 1; }
    if (!readable(SET_VEL, sizeof set_vel_sig, 0) || memcmp((void *)(uintptr_t)SET_VEL, set_vel_sig, sizeof set_vel_sig) ||
        !readable(SET_VEL_BODY, sizeof set_vel_body_sig, 0) ||
        memcmp((void *)(uintptr_t)SET_VEL_BODY, set_vel_body_sig, sizeof set_vel_body_sig)) {
        snprintf(why, n, "velocity routine differs from the analyzed build"); return 1;
    }
    uint64_t body = player_links(why, n);
    if (!body) { p_actor = 0; return 2; }
    uint64_t runtime = q(p_actor + 0x168);
    if (!readable(runtime + 0x1588, 8, 0) || !plausible(q(runtime + 0x1588)) || !readable(q(runtime + 0x1588), 8, 0) ||
        !plausible(q(q(runtime + 0x1588)))) { snprintf(why, n, "runtime lock invalid"); return 1; }
    __attribute__((aligned(16))) float vec[4] = {v[0], v[1], v[2], 0.0f};
    /* legs=1 (default since live player-4): the routine also re-poses the rider body and gives it v.
     * With legs=0 the rider keeps its velocity and the leg coupling drags the main body back. */
    int legs = ini_int(L"legs", 1) ? 1 : 0;
    diag(legs ? "set-before legs=1" : "set-before legs=0");
    ((SetVelocity)(uintptr_t)SET_VEL)((uintptr_t)p_actor, vec, (unsigned char)legs);
    diag("set-after");
    return 0;
}

/* ---- placement through the engine's own routine ----
 * 0x1413bcbb0(actor, const float4 pose[4] (16-byte aligned; rows 0..2 basis, row 3 translation),
 * const float4 *lin, const float4 *ang): requires actor+0x168, runs a validity check 0x1413a7460 on the
 * entity's current position, then 0x14140f990(runtime, pose, lin, ang): locks [runtime+0x1588], sets main-body
 * velocities (clamped) and pose (0x1418a8c20), unlocks, refreshes (0x14140a880), re-poses the rider through
 * 0x14140dd60 (legs 1), resets speed history; then 0x141408560([actor+0x190], runtime). Game callers: 7 sites
 * (0x1405367d4, 0x14053a005, 0x1405599ed, 0x140559bb9, 0x140561464, 0x140566709, 0x14056675e). */
#define PLACE 0x1413bcbb0ull
#define PLACE_RUNTIME 0x14140f990ull
static const unsigned char place_sig[] = {0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x6c, 0x24, 0x10, 0x48, 0x89, 0x74, 0x24, 0x18, 0x57,
                                          0x48, 0x83, 0xec, 0x30, 0x48, 0x83, 0xb9, 0x68, 0x01, 0x00, 0x00, 0x00, 0x49, 0x8b, 0xf9, 0x49};
static const unsigned char place_runtime_sig[] = {0x48, 0x8b, 0xc4, 0x48, 0x89, 0x58, 0x08, 0x48, 0x89, 0x70, 0x10, 0x48, 0x89, 0x78, 0x18, 0x4c,
                                                  0x89, 0x60, 0x20, 0x55, 0x41, 0x56, 0x41, 0x57, 0x48, 0x8d, 0x68, 0xb8, 0x48, 0x81, 0xec, 0x30};
typedef void (*Place)(uintptr_t actor, const float *pose, const float *lin, const float *ang);

static int player_set_pose(const float tr[16], const float lin[3], const float ang[3], char *why, size_t n) {
    if (!p_actor) { snprintf(why, n, "no player bound"); return 1; }
    if (!readable(PLACE, sizeof place_sig, 0) || memcmp((void *)(uintptr_t)PLACE, place_sig, sizeof place_sig) ||
        !readable(PLACE_RUNTIME, sizeof place_runtime_sig, 0) ||
        memcmp((void *)(uintptr_t)PLACE_RUNTIME, place_runtime_sig, sizeof place_runtime_sig)) {
        snprintf(why, n, "placement routine differs from the analyzed build"); return 1;
    }
    if (!player_links(why, n)) { p_actor = 0; return 2; }
    uint64_t runtime = q(p_actor + 0x168);
    if (!readable(runtime + 0x1588, 8, 0) || !plausible(q(runtime + 0x1588)) || !readable(q(runtime + 0x1588), 8, 0) ||
        !plausible(q(q(runtime + 0x1588)))) { snprintf(why, n, "runtime lock invalid"); return 1; }
    __attribute__((aligned(16))) float pose[16], l4[4] = {lin[0], lin[1], lin[2], 0}, a4[4] = {ang[0], ang[1], ang[2], 0};
    memcpy(pose, tr, sizeof pose);
    pose[3] = pose[7] = pose[11] = 0; pose[15] = 1.0f;
    diag("place-before");
    ((Place)(uintptr_t)PLACE)((uintptr_t)p_actor, pose, l4, a4);
    diag("place-after");
    return 0;
}

/* ---- in-process acquisition (run14/run34 chain) ----
 * manager = *0x14312d008; roots = *(manager+0x72) (unaligned), count = u16 at manager+0x7c; each root is a
 * 24-byte record whose payload (+0) is a world when flags (+0xc) bit31 is set. Accessor bytes at 0x1406a52f0
 * and 0x1406a5300 must match. For each world, scan registry entry 25 (world+0x770: pointer, signed count) for
 * receivers with the actor vtable, slot 0x270 == 0x140564ee0, +0x1050 == self, entity+0x60 == world. Exactly one
 * such actor across all worlds is required. */
#define ROOT_GLOBAL 0x14312d008ull
#define ROOT_ACC_A 0x1406a52f0ull
#define ROOT_ACC_B 0x1406a5300ull
#define ACTOR_UPDATE 0x140564ee0ull
static const unsigned char root_acc_a[] = {0x48, 0x8b, 0x05, 0x11, 0x7d, 0xa8, 0x02, 0x48, 0x8b, 0x40, 0x72, 0xc3};
static const unsigned char root_acc_b_tail[] = {0x0f, 0xb7, 0x48, 0x7c, 0x48, 0x8b, 0x40, 0x72, 0x48, 0x8d, 0x04, 0xc8, 0xc3};

/* Walk the live registries. Returns the number of matching actors; *found gets the last one. */
static int find_players(uint64_t *found, char *why, size_t n) {
    *found = 0;
    if (!readable(ROOT_ACC_A, sizeof root_acc_a, 0) || memcmp((void *)(uintptr_t)ROOT_ACC_A, root_acc_a, sizeof root_acc_a) ||
        !readable(ROOT_ACC_B, 7 + sizeof root_acc_b_tail, 0) ||
        memcmp((void *)(uintptr_t)(ROOT_ACC_B + 7), root_acc_b_tail, sizeof root_acc_b_tail)) {
        snprintf(why, n, "root accessors differ from the analyzed build"); return -1;
    }
    if (!readable(ROOT_GLOBAL, 8, 0)) { snprintf(why, n, "root global unreadable"); return -1; }
    uint64_t mgr = q(ROOT_GLOBAL);
    if (!plausible(mgr) || !readable(mgr + 0x72, 12, 0)) { snprintf(why, n, "root manager invalid"); return -1; }
    uint64_t roots; memcpy(&roots, (const void *)(uintptr_t)(mgr + 0x72), 8);
    uint16_t count = *(volatile uint16_t *)(uintptr_t)(mgr + 0x7c);
    if (count > 16 || (count && (!plausible(roots) || !readable(roots, 8u * count, 0)))) { snprintf(why, n, "root array invalid"); return -1; }
    int matches = 0;
    for (unsigned i = 0; i < count; i++) {
        uint64_t rec = q(roots + 8u * i);
        if (!plausible(rec) || !readable(rec, 24, 0)) continue;
        if (*(volatile int32_t *)(uintptr_t)(rec + 0xc) >= 0) continue;          /* inactive */
        uint64_t world = q(rec);
        if (!plausible(world) || !readable(world + 0x770, 16, 0)) continue;
        uint64_t arr = q(world + 0x770);
        int64_t cnt = *(volatile int32_t *)(uintptr_t)(world + 0x778);
        if (cnt <= 0 || cnt > 256 || !plausible(arr) || !readable(arr, 8u * (size_t)cnt, 0)) continue;
        for (int64_t k = 0; k < cnt; k++) {
            uint64_t a = q(arr + 8u * (uint64_t)k);
            if (!plausible(a) || !readable(a, 0x1058, 0) || q(a) != ACTOR_VT) continue;
            if (!readable(ACTOR_VT + 0x270, 8, 0) || q(ACTOR_VT + 0x270) != ACTOR_UPDATE) continue;
            if (q(a + 0x1050) != a) continue;
            uint64_t e = q(a + 0x10);
            if (!plausible(e) || !readable(e + 0x60, 8, 0) || q(e + 0x60) != world) continue;
            *found = a; matches++;
        }
    }
    if (!matches) snprintf(why, n, "no player found");
    else if (matches > 1) snprintf(why, n, "%d candidate players (need exactly one)", matches);
    return matches;
}

static int player_acquire(int *world_changed, char *why, size_t n) {
    uint64_t found;
    p_actor = p_entity = p_world = 0;
    *world_changed = 0;
    if (find_players(&found, why, n) != 1) return 1;
    p_actor = found;
    if (!player_links(why, n)) { p_actor = 0; return 1; }
    p_entity = q(found + 0x10); p_world = q(p_entity + 0x60);
    *world_changed = last_world && last_world != p_world;
    last_world = p_world;
    return 0;
}

/* The binding is live only while the registries still hold exactly this actor. */
static int player_check(char *why, size_t n) {
    if (!p_actor) { snprintf(why, n, "no player bound"); return 1; }
    uint64_t found;
    int m = find_players(&found, why, n);
    if (m == 1 && found == p_actor && player_links(why, n)) return 0;
    if (m == 1 && found != p_actor) snprintf(why, n, "a different player is registered");
    else if (m == 1) { /* links failed; why already set */ }
    p_actor = 0;
    return 1;
}

/* Passive animation reads only. RPM copies safely across inaccessible pages;
 * before/after equality is not object lifetime or animation-completion proof. */
static int animation_read(void *context, uint64_t address, void *out, size_t size) {
    (void)context;
    if (address < 0x10000 || address >= 0x800000000000ull || size > 0x800000000000ull-address) return 0;
    SIZE_T got=0;
    return ReadProcessMemory(GetCurrentProcess(),(LPCVOID)(uintptr_t)address,out,size,&got) && got==size;
}
static int animation_channel(uint32_t key, SnowAnimationChannelRaw *out, char *why, size_t n) {
    memset(out,0,sizeof *out);
    if (!p_actor || player_check(why,n)) return 2;
    const uint64_t actor=p_actor, entity=p_entity, world=p_world;
    uint64_t addresses[4]={actor,actor+0x1050,actor+0x10,entity+0x60};
    uint64_t expected[4]={ACTOR_VT,actor,entity,world};
    for (unsigned i=0;i<4;i++) {
        uint64_t value;
        if (!animation_read(NULL,addresses[i],&value,8) || value!=expected[i]) {
            snprintf(why,n,"player animation identity changed"); return 2;
        }
    }
    const SnowAnimationProfile profile={
        {0x141ebbf78ull,0x141ebcbd8ull,0x141ec7160ull},
        0x141f1e598ull,0x140d4ba80ull,0x142e78a30ull,3};
    SnowAnimationChannelRaw result={0};
    if (snow_animation_observe(animation_read,NULL,entity,&profile,key,&result)) {
        snprintf(why,n,"animation observation refused: identity, bounds, read or endpoint mismatch"); return 1;
    }
    for (unsigned i=0;i<4;i++) {
        uint64_t value;
        if (!animation_read(NULL,addresses[i],&value,8) || value!=expected[i]) {
            snprintf(why,n,"player animation identity changed"); return 2;
        }
    }
    if (p_actor!=actor || p_entity!=entity || p_world!=world || player_check(why,n)) return 2;
    *out=result; return 0;
}

static int cached_parent(SnowCachedParentRaw *out, char *why, size_t n) {
    memset(out,0,sizeof *out);
    if (!p_actor || player_check(why,n)) return 2;
    const uint64_t actor=p_actor, entity=p_entity, world=p_world;
    uint64_t addresses[4]={actor,actor+0x1050,actor+0x10,entity+0x60};
    uint64_t expected[4]={ACTOR_VT,actor,entity,world};
    for (unsigned i=0;i<4;i++) {
        uint64_t value;
        if (!animation_read(NULL,addresses[i],&value,8) || value!=expected[i]) {
            snprintf(why,n,"player animation identity changed"); return 2;
        }
    }
    const SnowAnimationProfile profile={
        {0x141ebbf78ull,0x141ebcbd8ull,0x141ec7160ull},
        0x141f1e598ull,0x140d4ba80ull,0x142e78a30ull,3};
    SnowCachedParentRaw result={0};
    if (snow_cached_parent_observe(animation_read,NULL,entity,&profile,&result)) {
        snprintf(why,n,"animation observation refused: identity, bounds, read or endpoint mismatch"); return 1;
    }
    for (unsigned i=0;i<4;i++) {
        uint64_t value;
        if (!animation_read(NULL,addresses[i],&value,8) || value!=expected[i]) {
            snprintf(why,n,"player animation identity changed"); return 2;
        }
    }
    if (p_actor!=actor || p_entity!=entity || p_world!=world || player_check(why,n)) return 2;
    *out=result; return 0;
}

const SnowAdapter snow_adapter = {"steep-analyzed-build", bind, read, cas_group, enter, leave, player_bind, player_read,
                                  player_set_velocity, player_acquire, player_check, player_set_pose, animation_channel, cached_parent};


int snow_steep_probe_binding(SnowUpdateBinding *out,SnowUpdateOriginal *original,char *why,size_t n) {
    int changed=0;
    if(out) memset(out,0,sizeof *out);
    if(original) *original=NULL;
    if(!out || !original || !why || !n) return 1;
    SnowCounters before,after;
    if(bind(why,n) || read(&before,why,n)) return 1;
    if(!SNOW_GROUP_HELD(before.group)) { snprintf(why,n,"probe acquisition requires held simulation"); return 1; }
    if(player_acquire(&changed,why,n) || player_check(why,n)) return 1;
    const uint64_t actor=p_actor,world=p_world;
    const SnowUpdateProfile profile={ACTOR_VT,RUNTIME_VT,0x14053ec30ull,0x1408ab390ull};
    SnowUpdateBinding result;
    if(!snow_update_resolve_binding(animation_read,NULL,actor,&profile,&result)) {
        snprintf(why,n,"snow-update owner/counter binding refused"); return 1;
    }
    if(result.world!=world || player_check(why,n) || p_actor!=actor || p_world!=world) {
        snprintf(why,n,"player registration changed during probe binding"); return 1;
    }
    if(read(&after,why,n) || after.owner!=before.owner || after.group!=before.group ||
       after.step!=before.step || !SNOW_GROUP_HELD(after.group)) {
        snprintf(why,n,"engine hold changed during probe acquisition"); return 1;
    }
    *out=result; *original=(SnowUpdateOriginal)(uintptr_t)profile.original_target;
    return 0;
}
