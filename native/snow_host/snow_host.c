/* Snow mod host: persistent late-loaded host with a loopback command channel
 * and native plugins (snow_plugin.h, managed by snow_plugins.c).
 *
 * DllMain does nothing. SnowHost_Start (run once on a new thread after
 * LoadLibraryW returns) starts two threads:
 *   io thread       - accepts one 127.0.0.1 client at a time and parses requests.
 *                     It never touches game memory.
 *   executor thread - the only thread that calls the adapter. Commands run
 *                     serially. It also owns the recovery lease: a host-held
 *                     pause is released when the lease expires or the client
 *                     disconnects.
 * Protocol: one JSON object per line. See README.md.
 */
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <stdarg.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "snow_adapter.h"
#include "snow_plugins.h"
#include "snow_step_contract.h"

#define HOST_VERSION SNOW_HOST_VERSION
#define API_VERSION 1
#define DEFAULT_PORT 47017
#define MAX_LINE 4096
#define MAX_REPLY 16384
#define MAX_STEPS 60
#define DEFAULT_LEASE_MS 30000
#define MAX_LEASE_MS 300000
#define STEP_TIMEOUT_MS 2000

typedef struct Request {
    long long id;
    char method[48];
    long long count, lease_ms, channel_key;
    int has_channel_key;
    char handle[48];
    double vel[3], pos[3], delta_speed;
    int has_delta_speed;
    int has_id, has_count, has_lease, has_handle, has_vel, has_pos;
} Request;

static HMODULE self;
static LONG started;
static unsigned short port;
static WCHAR dir[MAX_PATH];
static CRITICAL_SECTION log_lock;
static HANDLE work_ev, done_ev;
static Request pending;
static char reply[MAX_REPLY];
static int reply_ok;
static char bind_why[160];
static int bound;
static int engine_ready, plugins_initialized;

/* Executor-owned state. */
static int host_paused, faulted;
static uint32_t pause_baseline;
static uint64_t pause_owner;
static DWORD lease_ms;
static ULONGLONG lease_deadline;
static char last_recovery[96];
static long long commands_completed, commands_failed;
static uint64_t steps_released;
static int player_bound;
static uint64_t player_generation;   /* opaque player identity exposed to clients and plugins */
#define WATCH_MS 250
/* Player events are queued wherever a change is noticed (possibly on the plugin thread inside a plugin's
 * get_player) and delivered only from the executor, between commands and on the watch tick. */
static SnowPlayerEventV1 pending_events[8];
static int pending_count;
static ULONGLONG start_tick;
static LARGE_INTEGER qpf;

/* ---------- logging and output ---------- */

#define host_log snow_host_log

void snow_host_log(const char *tag, const char *fmt, ...) {
    WCHAR path[MAX_PATH];
    if (_snwprintf(path, MAX_PATH, L"%ls\\snow_host.log", dir) < 0) return;
    char line[512];
    SYSTEMTIME t; GetSystemTime(&t);
    int n = snprintf(line, sizeof line, "%04d-%02d-%02dT%02d:%02d:%02d.%03dZ [%s] ",
                     t.wYear, t.wMonth, t.wDay, t.wHour, t.wMinute, t.wSecond, t.wMilliseconds, tag);
    va_list ap; va_start(ap, fmt);
    n += vsnprintf(line + n, sizeof line - n - 2, fmt, ap);
    va_end(ap);
    if (n > (int)sizeof line - 2) n = sizeof line - 2;
    line[n++] = '\n';
    EnterCriticalSection(&log_lock);
    HANDLE f = CreateFileW(path, FILE_APPEND_DATA, FILE_SHARE_READ, NULL, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (f != INVALID_HANDLE_VALUE) { DWORD w; WriteFile(f, line, n, &w, NULL); CloseHandle(f); }
    LeaveCriticalSection(&log_lock);
}

typedef struct Out { char *p; size_t n, len; } Out;
static void put(Out *o, const char *fmt, ...) {
    if (o->len >= o->n) return;
    va_list ap; va_start(ap, fmt);
    int k = vsnprintf(o->p + o->len, o->n - o->len, fmt, ap);
    va_end(ap);
    if (k > 0) o->len = (o->len + k < o->n) ? o->len + k : o->n;
}
static void put_group(Out *o, uint32_t g) {
    put(o, "\"%02x%02x%02x%02x\"", SNOW_GROUP_BYTE(g, 0), SNOW_GROUP_BYTE(g, 1), SNOW_GROUP_BYTE(g, 2), SNOW_GROUP_BYTE(g, 3));
}
static void put_str(Out *o, const char *s) {
    put(o, "\"");
    for (; *s; s++) put(o, (*s == '"' || *s == '\\') ? "\\%c" : ((unsigned char)*s < 0x20 ? " " : "%c"), *s);
    put(o, "\"");
}

static void write_marker(const char *state) {
    WCHAR path[MAX_PATH];
    if (_snwprintf(path, MAX_PATH, L"%ls\\snow_host.json", dir) < 0) return;
    FILETIME c, e, k, u; GetProcessTimes(GetCurrentProcess(), &c, &e, &k, &u);
    char buf[512]; Out o = {buf, sizeof buf, 0};
    put(&o, "{\"host_version\":\"%s\",\"api_version\":%d,\"state\":\"%s\",\"pid\":%lu,\"created\":\"%llx\",\"port\":%u,\"adapter\":",
        HOST_VERSION, API_VERSION, state, GetCurrentProcessId(),
        ((unsigned long long)c.dwHighDateTime << 32) | c.dwLowDateTime, port);
    put_str(&o, snow_adapter.name);
    put(&o, ",\"bound\":%s,\"bind_error\":", bound ? "true" : "false");
    put_str(&o, bound ? "" : bind_why);
    put(&o, "}\n");
    HANDLE f = CreateFileW(path, GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (f != INVALID_HANDLE_VALUE) { DWORD w; WriteFile(f, buf, (DWORD)o.len, &w, NULL); CloseHandle(f); }
}

/* ---------- request parsing (strict, small subset of JSON) ---------- */

static const char *ws(const char *s) { while (*s == ' ' || *s == '\t' || *s == '\r') s++; return s; }
static const char *parse_str(const char *s, char *dst, size_t n) {
    if (*s != '"') return NULL;
    size_t k = 0;
    for (s++; *s != '"'; s++) {
        if (!*s || *s == '\\' || (unsigned char)*s < 0x20 || k + 1 >= n) return NULL;
        dst[k++] = *s;
    }
    dst[k] = 0;
    return s + 1;
}
static const char *parse_int(const char *s, long long *v) {
    char *end; long long x = strtoll(s, &end, 10);
    if (end == s || *end == '.' || *end == 'e' || *end == 'E') return NULL;
    *v = x; return end;
}
static const char *parse_num(const char *s, double *v) {
    char *end; double x = strtod(s, &end);
    if (end == s || x != x || x > 1e30 || x < -1e30) return NULL;
    *v = x; return end;
}
static const char *parse_params(const char *s, Request *r) {
    s = ws(s); if (*s++ != '{') return NULL;
    s = ws(s); if (*s == '}') return s + 1;
    for (;;) {
        char key[24];
        if (!(s = parse_str(ws(s), key, sizeof key))) return NULL;
        s = ws(s); if (*s++ != ':') return NULL;
        s = ws(s);
        if (!strcmp(key, "count")) { if (!(s = parse_int(s, &r->count))) return NULL; r->has_count = 1; }
        else if (!strcmp(key, "key")) { if (r->has_channel_key || !(s = parse_int(s, &r->channel_key))) return NULL; r->has_channel_key = 1; }
        else if (!strcmp(key, "delta_speed")) { if (r->has_delta_speed || !(s = parse_num(s, &r->delta_speed))) return NULL; r->has_delta_speed = 1; }
        else if (!strcmp(key, "lease_ms")) { if (!(s = parse_int(s, &r->lease_ms))) return NULL; r->has_lease = 1; }
        else if (!strcmp(key, "vx") || !strcmp(key, "vy") || !strcmp(key, "vz")) {
            int k = key[1] - 'x';
            if (!(s = parse_num(s, &r->vel[k]))) return NULL;
            r->has_vel |= 1 << k;
        }
        else if (!strcmp(key, "px") || !strcmp(key, "py") || !strcmp(key, "pz")) {
            int k = key[1] - 'x';
            if (!(s = parse_num(s, &r->pos[k]))) return NULL;
            r->has_pos |= 1 << k;
        }
        else if (!strcmp(key, "handle")) { if (!(s = parse_str(s, r->handle, sizeof r->handle))) return NULL; r->has_handle = 1; }
        else return NULL;
        s = ws(s);
        if (*s == ',') { s++; continue; }
        if (*s == '}') return s + 1;
        return NULL;
    }
}
static int parse_request(const char *s, Request *r) {
    memset(r, 0, sizeof *r);
    s = ws(s); if (*s++ != '{') return 0;
    for (;;) {
        char key[16];
        if (!(s = parse_str(ws(s), key, sizeof key))) return 0;
        s = ws(s); if (*s++ != ':') return 0;
        s = ws(s);
        if (!strcmp(key, "id")) { if (!(s = parse_int(s, &r->id))) return 0; r->has_id = 1; }
        else if (!strcmp(key, "method")) { if (!(s = parse_str(s, r->method, sizeof r->method))) return 0; }
        else if (!strcmp(key, "params")) { if (!(s = parse_params(s, r))) return 0; }
        else return 0;
        s = ws(s);
        if (*s == ',') { s++; continue; }
        if (*s == '}') break;
        return 0;
    }
    return *ws(s + 1) == 0 && r->has_id && r->method[0];
}

/* ---------- executor: the only code that calls the adapter ---------- */

/* Plugin API get_state. Runs on the plugin thread while the executor waits. */
void snow_host_state(SnowHostStateV1 *out) {
    out->host_paused = (uint32_t)host_paused;
    out->steps_released = steps_released;
}

static void queue_event(uint32_t kind, uint64_t identity, int world_changed) {
    if (pending_count == (int)(sizeof pending_events / sizeof *pending_events)) return;
    SnowPlayerEventV1 e = {sizeof e, kind, identity, (uint32_t)(world_changed != 0), 0};
    pending_events[pending_count++] = e;
}

static void drop_binding(const char *why) {
    if (!player_bound) return;
    player_bound = 0;
    host_log("player", "binding dropped: %s", why);
    queue_event(SNOW_PLAYER_LOST, player_generation, 0);
}

/* In-process acquisition; queues ACQUIRED on success. */
static int acquire_now(char *why, size_t n) {
    int world_changed = 0;
    if (!snow_adapter.player_acquire || snow_adapter.player_acquire(&world_changed, why, n)) return 0;
    player_bound = 1; player_generation++;
    host_log("player", "acquired in-process (identity %llu%s)", (unsigned long long)player_generation,
             world_changed ? ", new world" : "");
    queue_event(SNOW_PLAYER_ACQUIRED, player_generation, world_changed);
    return 1;
}

/* Executor only: deliver queued events to plugins. */
static void flush_events(void) {
    for (int i = 0; i < pending_count; i++) {
        host_log("player", "event %s identity %llu%s", pending_events[i].kind == SNOW_PLAYER_ACQUIRED ? "acquired" : "lost",
                 (unsigned long long)pending_events[i].identity, pending_events[i].world_changed ? " (new world)" : "");
        snow_plugins_on_player(&pending_events[i]);
    }
    pending_count = 0;
}

/* Executor only, about every WATCH_MS: check the binding against the engine's registries, re-acquire. */
static void watch_tick(void) {
    if (!bound) return;
    char why[160] = "";
    if (player_bound && snow_adapter.player_check && snow_adapter.player_check(why, sizeof why)) drop_binding(why);
    if (!player_bound) acquire_now(why, sizeof why);
    flush_events();
}

/* Read the bound player's body. Executor context (or the plugin thread while the executor waits). */
static int player_fill(SnowPlayerStateV1 *out, char *why, size_t n) {
    why[0] = 0;
    if (!bound || !snow_adapter.player_read) { snprintf(why, n, "player state unsupported"); return SNOW_E_NO_PLAYER; }
    if (!player_bound && !acquire_now(why, n)) {
        /* Nothing bound and no in-process acquisition. */
        if (!why[0]) snprintf(why, n, "no player bound");
        return SNOW_E_NO_PLAYER;
    }
    if (snow_adapter.player_check && snow_adapter.player_check(why, n)) { drop_binding(why); return SNOW_E_PLAYER_CHANGED; }
    SnowPlayerRaw r;
    int rc = snow_adapter.player_read(&r, why, n);
    if (rc == 2) { drop_binding(why); return SNOW_E_PLAYER_CHANGED; }
    if (rc) return SNOW_E_NO_PLAYER;
    out->flags = r.flags;
    out->identity = player_generation;
    for (int k = 0; k < 3; k++) {
        out->position[k] = r.transform[12 + k];
        for (int c = 0; c < 3; c++) out->axes[c][k] = r.transform[4 * c + k];
        out->linear_velocity[k] = r.linear_velocity[k];
        out->angular_velocity[k] = r.angular_velocity[k];
    }
    return SNOW_OK;
}

/* Plugin API get_player: only while the host holds the simulation, so the body is not being stepped. */
int snow_host_player(SnowPlayerStateV1 *out) {
    if (!host_paused) return SNOW_E_NOT_HELD;
    char why[160];
    return player_fill(out, why, sizeof why);
}

/* Velocity assignment, executor context or plugin thread while the executor waits. Held only. */
static int player_set(const float v[3], char *why, size_t n) {
    why[0] = 0;
    if (!host_paused) { snprintf(why, n, "simulation not held by host"); return SNOW_E_NOT_HELD; }
    if (!bound || !player_bound) { snprintf(why, n, "no player bound"); return SNOW_E_NO_PLAYER; }
    if (!snow_adapter.player_set_velocity) { snprintf(why, n, "adapter has no velocity setter"); return SNOW_E_REFUSED; }
    double m2 = 0;
    for (int k = 0; k < 3; k++) {
        if (!(v[k] == v[k]) || v[k] > 1e6f || v[k] < -1e6f) { snprintf(why, n, "non-finite velocity"); return SNOW_E_REFUSED; }
        m2 += (double)v[k] * v[k];
    }
    if (m2 > (double)SNOW_MAX_SET_SPEED * SNOW_MAX_SET_SPEED) { snprintf(why, n, "speed above %.0f", SNOW_MAX_SET_SPEED); return SNOW_E_REFUSED; }
    SnowPlayerStateV1 cur = {sizeof cur, 0, 0, {0}, {{0}}, {0}, {0}};
    int rc = player_fill(&cur, why, n);
    if (rc) return rc;
    if ((cur.flags & SNOW_PLAYER_FLAGS_VALID) && !(cur.flags & SNOW_PLAYER_IN_WORLD)) { snprintf(why, n, "player body is not being simulated"); return SNOW_E_REFUSED; }
    rc = snow_adapter.player_set_velocity(v, why, n);
    if (rc == 2) { drop_binding(why); return SNOW_E_PLAYER_CHANGED; }
    if (rc) return SNOW_E_REFUSED;
    host_log("player", "velocity set to (%.3f, %.3f, %.3f)", v[0], v[1], v[2]);
    return SNOW_OK;
}

static int finite3(const float *v) {
    for (int k = 0; k < 3; k++) if (!(v[k] == v[k]) || v[k] > 1e7f || v[k] < -1e7f) return 0;
    return 1;
}

/* Placement, same contexts as player_set. Validates before the adapter is called. */
static int player_place(const SnowPlayerStateV1 *t, char *why, size_t n) {
    why[0] = 0;
    if (!host_paused) { snprintf(why, n, "simulation not held by host"); return SNOW_E_NOT_HELD; }
    if (!bound || !player_bound) { snprintf(why, n, "no player bound"); return SNOW_E_NO_PLAYER; }
    if (!snow_adapter.player_set_pose) { snprintf(why, n, "adapter has no placement routine"); return SNOW_E_REFUSED; }
    if (!finite3(t->position) || !finite3(t->linear_velocity) || !finite3(t->angular_velocity) ||
        !finite3(t->axes[0]) || !finite3(t->axes[1]) || !finite3(t->axes[2])) { snprintf(why, n, "non-finite value"); return SNOW_E_REFUSED; }
    for (int a = 0; a < 3; a++)
        for (int b = a; b < 3; b++) {
            double d = 0;
            for (int k = 0; k < 3; k++) d += (double)t->axes[a][k] * t->axes[b][k];
            if (fabs(d - (a == b ? 1.0 : 0.0)) > 1e-3) { snprintf(why, n, "axes not orthonormal"); return SNOW_E_REFUSED; }
        }
    double sv = 0, sw = 0;
    for (int k = 0; k < 3; k++) { sv += (double)t->linear_velocity[k] * t->linear_velocity[k]; sw += (double)t->angular_velocity[k] * t->angular_velocity[k]; }
    if (sv > (double)SNOW_MAX_SET_SPEED * SNOW_MAX_SET_SPEED || sw > 1e4) { snprintf(why, n, "velocity above limit"); return SNOW_E_REFUSED; }
    SnowPlayerStateV1 cur = {sizeof cur, 0, 0, {0}, {{0}}, {0}, {0}};
    int rc = player_fill(&cur, why, n);
    if (rc) return rc;
    if ((cur.flags & SNOW_PLAYER_FLAGS_VALID) && !(cur.flags & SNOW_PLAYER_IN_WORLD)) { snprintf(why, n, "player body is not being simulated"); return SNOW_E_REFUSED; }
    double dist2 = 0;
    for (int k = 0; k < 3; k++) dist2 += ((double)t->position[k] - cur.position[k]) * ((double)t->position[k] - cur.position[k]);
    if (dist2 > (double)SNOW_MAX_TELEPORT_DISTANCE * SNOW_MAX_TELEPORT_DISTANCE) { snprintf(why, n, "move of %.1f exceeds %.0f", sqrt(dist2), SNOW_MAX_TELEPORT_DISTANCE); return SNOW_E_REFUSED; }
    float tr[16] = {0};
    for (int c = 0; c < 3; c++) for (int k = 0; k < 3; k++) tr[4 * c + k] = t->axes[c][k];
    for (int k = 0; k < 3; k++) tr[12 + k] = t->position[k];
    tr[15] = 1.0f;
    if (snow_adapter.player_check && snow_adapter.player_check(why, n)) { drop_binding(why); return SNOW_E_PLAYER_CHANGED; }
    rc = snow_adapter.player_set_pose(tr, t->linear_velocity, t->angular_velocity, why, n);
    if (rc == 2) { drop_binding(why); return SNOW_E_PLAYER_CHANGED; }
    if (rc) return SNOW_E_REFUSED;
    host_log("player", "placed at (%.3f, %.3f, %.3f), moved %.3f", t->position[0], t->position[1], t->position[2], sqrt(dist2));
    return SNOW_OK;
}

int snow_host_set_pose(const SnowPlayerStateV1 *target) {
    char why[160];
    return player_place(target, why, sizeof why);
}

int snow_host_set_velocity(const float v[3]) {
    char why[160];
    return player_set(v, why, sizeof why);
}

static void put_vec(Out *o, const char *name, const float *v) {
    put(o, ",\"%s\":[%.9g,%.9g,%.9g]", name, v[0], v[1], v[2]);
}

static int do_player_bind(const Request *r, Out *o) {
    char why[160] = "";
    if (!r->has_handle && !snow_adapter.player_acquire) { put(o, "\"error\":\"bad_params\",\"detail\":\"handle required\""); return 0; }
    if (r->has_handle && !snow_adapter.player_bind) { put(o, "\"error\":\"unsupported\""); return 0; }
    drop_binding("rebind requested");
    if (!r->has_handle) {
        /* No handle: in-process acquisition. */
        if (!acquire_now(why, sizeof why)) { put(o, "\"error\":\"player_rejected\",\"detail\":"); put_str(o, why); return 0; }
    } else {
        if (snow_adapter.player_bind(r->handle, why, sizeof why)) {
            put(o, "\"error\":\"player_rejected\",\"detail\":"); put_str(o, why); return 0;
        }
        player_bound = 1; player_generation++;
        queue_event(SNOW_PLAYER_ACQUIRED, player_generation, 0);
    }
    SnowPlayerStateV1 st = {sizeof st, 0, 0, {0}, {{0}}, {0}, {0}};
    int rc = player_fill(&st, why, sizeof why);
    if (rc) { put(o, "\"error\":\"player_rejected\",\"detail\":"); put_str(o, why); return 0; }
    put(o, "\"identity\":%llu", (unsigned long long)st.identity);
    return 1;
}

static int do_player_get(Out *o);
static int do_player_set_velocity(const Request *r, Out *o) {
    if (r->has_vel != 7) { put(o, "\"error\":\"bad_params\",\"detail\":\"vx, vy and vz required\""); return 0; }
    float v[3] = {(float)r->vel[0], (float)r->vel[1], (float)r->vel[2]};
    char why[160];
    int rc = player_set(v, why, sizeof why);
    if (rc) {
        static const char *names[] = {"ok", "bad_params", "not_paused_by_host", "no_player", "player_changed", "refused"};
        put(o, "\"error\":\"%s\",\"detail\":", names[rc]); put_str(o, why); return 0;
    }
    put(o, "\"set\":[%.9g,%.9g,%.9g],\"after\":{", v[0], v[1], v[2]);
    int ok = do_player_get(o);
    put(o, "}");
    return ok;
}

/* Authored one-shot mod policy, not a recovered gameplay rule. No per-tick hook.
 * Resolve/read/adjust on the executor under a host hold, so clients never send a
 * velocity calculated from a stale running snapshot. Scale the full 3D vector. */
static int do_player_adjust_speed(const Request *r, Out *o) {
    if (!r->has_delta_speed || !isfinite(r->delta_speed) || r->delta_speed == 0 ||
        fabs(r->delta_speed) > 10 || r->has_vel || r->has_pos || r->has_handle || r->has_count || r->has_lease) {
        put(o, "\"error\":\"bad_params\",\"detail\":\"delta_speed must be nonzero and within -10..10\""); return 0;
    }
    if (!host_paused) { put(o, "\"error\":\"not_paused_by_host\""); return 0; }
    SnowPlayerStateV1 cur = {sizeof cur, 0, 0, {0}, {{0}}, {0}, {0}};
    char why[160];
    int rc = player_fill(&cur, why, sizeof why);
    if (rc) { put(o, "\"error\":\"player_rejected\",\"detail\":"); put_str(o, why); return 0; }
    if ((cur.flags & (SNOW_PLAYER_FLAGS_VALID | SNOW_PLAYER_IN_WORLD)) !=
        (SNOW_PLAYER_FLAGS_VALID | SNOW_PLAYER_IN_WORLD)) {
        put(o, "\"error\":\"player_not_in_world\""); return 0;
    }
    if (!finite3(cur.linear_velocity) || !finite3(cur.angular_velocity)) {
        put(o, "\"error\":\"invalid_player_velocity\""); return 0;
    }
    double speed2 = 0, spin2 = 0;
    for (int k = 0; k < 3; k++) {
        speed2 += (double)cur.linear_velocity[k] * cur.linear_velocity[k];
        spin2 += (double)cur.angular_velocity[k] * cur.angular_velocity[k];
    }
    /* The engine setter clears angular velocity. Refuse obvious spinning;
     * this threshold is our conservative policy, not a grounded/trick detector. */
    if (spin2 > 0.25 * 0.25) { put(o, "\"error\":\"player_rotating\""); return 0; }
    double speed = sqrt(speed2);
    if (speed < 0.5) { put(o, "\"error\":\"direction_unresolved\""); return 0; }
    if (r->delta_speed > 0 && speed >= 60) { put(o, "\"error\":\"boost_speed_cap\""); return 0; }
    double target = fmax(0, speed + r->delta_speed);
    if (r->delta_speed > 0) target = fmin(60, target);
    float v[3];
    for (int k = 0; k < 3; k++) v[k] = (float)(cur.linear_velocity[k] * (target / speed));
    rc = player_set(v, why, sizeof why);
    if (rc) { put(o, "\"error\":\"adjust_refused\",\"detail\":"); put_str(o, why); return 0; }
    put(o, "\"identity\":%llu,\"speed_before\":%.9g,\"speed_target\":%.9g",
        (unsigned long long)cur.identity, speed, target);
    put_vec(o, "velocity_before", cur.linear_velocity);
    put(o, ",\"angular_velocity_reset\":true,\"after\":{");
    int ok = do_player_get(o);
    put(o, "}");
    return ok;
}

static int do_player_set_position(const Request *r, Out *o) {
    if (r->has_pos != 7 || (r->has_vel && r->has_vel != 7)) {
        put(o, "\"error\":\"bad_params\",\"detail\":\"px, py and pz required; vx, vy, vz all or none\""); return 0;
    }
    static const char *names[] = {"ok", "bad_params", "not_paused_by_host", "no_player", "player_changed", "refused"};
    char why[160];
    SnowPlayerStateV1 t = {sizeof t, 0, 0, {0}, {{0}}, {0}, {0}};
    int rc = host_paused ? player_fill(&t, why, sizeof why) : SNOW_E_NOT_HELD;
    if (rc == SNOW_E_NOT_HELD) snprintf(why, sizeof why, "simulation not held by host");
    if (!rc) {
        for (int k = 0; k < 3; k++) {
            t.position[k] = (float)r->pos[k];
            if (r->has_vel) t.linear_velocity[k] = (float)r->vel[k];
        }
        rc = player_place(&t, why, sizeof why);
    }
    if (rc) { put(o, "\"error\":\"%s\",\"detail\":", names[rc]); put_str(o, why); return 0; }
    put(o, "\"set\":[%.9g,%.9g,%.9g],\"after\":{", t.position[0], t.position[1], t.position[2]);
    int ok = do_player_get(o);
    put(o, "}");
    return ok;
}

static int do_player_get(Out *o) {
    SnowPlayerStateV1 st = {sizeof st, 0, 0, {0}, {{0}}, {0}, {0}};
    char why[160];
    int rc = player_fill(&st, why, sizeof why);
    if (rc) {
        put(o, "\"error\":\"%s\",\"detail\":", rc == SNOW_E_PLAYER_CHANGED ? "player_changed" : "no_player");
        put_str(o, why); return 0;
    }
    /* Outside a host-held pause the reads race the simulation and are not a consistent snapshot. */
    put(o, "\"identity\":%llu,\"held\":%s,\"flags\":%u", (unsigned long long)st.identity, host_paused ? "true" : "false", st.flags);
    put_vec(o, "position", st.position);
    put(o, ",\"axes\":[[%.9g,%.9g,%.9g],[%.9g,%.9g,%.9g],[%.9g,%.9g,%.9g]]",
        st.axes[0][0], st.axes[0][1], st.axes[0][2], st.axes[1][0], st.axes[1][1], st.axes[1][2],
        st.axes[2][0], st.axes[2][1], st.axes[2][2]);
    put_vec(o, "linear_velocity", st.linear_velocity);
    put_vec(o, "angular_velocity", st.angular_velocity);
    return 1;
}

static int do_cached_parent(Out *o) {
    if (!snow_adapter.cached_parent) { put(o,"\"error\":\"animation_unsupported\""); return 0; }
    SnowPlayerStateV1 player={0}; player.struct_size=sizeof player;
    char why[160]="";
    if (player_fill(&player,why,sizeof why)) { put(o,"\"error\":\"no_player\",\"detail\":"); put_str(o,why); return 0; }
    SnowCachedParentRaw result={0};
    int rc=snow_adapter.cached_parent(&result,why,sizeof why);
    if (rc==2) drop_binding(why);
    if (rc || result.guards_matched!=1) { put(o,"\"error\":\"animation_observation_refused\",\"detail\":"); put_str(o,why); return 0; }
    const float *poses[]={result.cached,result.primary,result.current};
    for (unsigned i=0;i<3;i++) for(unsigned j=0;j<8;j++) if(!isfinite(poses[i][j])) {
        put(o,"\"error\":\"invalid_animation_value\""); return 0;
    }
    const uint32_t flags[]={result.primary_present,result.current_present,result.banks_alias,
        result.storage_nonempty,result.context_nonzero,result.function_present,result.holder_present,
        result.target_present,result.status_sign,result.eligible};
    const char *names[]={"primary_present","current_present","banks_alias","callback_storage_nonempty",
        "forwarded_context_nonzero","function_present","holder_present","holder_target_present",
        "holder_status_sign_bit","callback_eligible"};
    for(unsigned i=0;i<10;i++) if(flags[i]>1) {put(o,"\"error\":\"invalid_animation_value\"");return 0;}
    if(result.context_tag>3) {put(o,"\"error\":\"invalid_animation_value\"");return 0;}
    put(o,"\"identity\":%llu,\"guards_matched\":true,\"context_tag\":%u,"
        "\"atomic_snapshot\":false,\"lifetime_pinned\":false,\"invocation_observed\":false,"
        "\"writer_attribution_established\":false,\"executable_memory_verified\":false,"
        "\"safe_native_call_established\":false,\"adapter\":",(unsigned long long)player.identity,result.context_tag);
    put_str(o,snow_adapter.name);
    for(unsigned i=0;i<10;i++) put(o,",\"%s\":%s",names[i],flags[i]?"true":"false");
    const char *pose_names[]={"cached_parent","primary_parent","current_parent"};
    for(unsigned i=0;i<3;i++) {
        put(o,",\"%s\":",pose_names[i]);
        if ((i==1 && !result.primary_present)||(i==2 && !result.current_present)) {put(o,"null");continue;}
        put(o,"[");for(unsigned j=0;j<8;j++)put(o,"%s%.9g",j?",":"",poses[i][j]);put(o,"]");
    }
    return 1;
}

static int do_animation_channel(const Request *r, Out *o) {
    if (!r->has_channel_key || r->channel_key < 0 || r->channel_key > 4294967295LL) {
        put(o, "\"error\":\"invalid_channel_key\""); return 0;
    }
    if (!snow_adapter.animation_channel) { put(o, "\"error\":\"animation_unsupported\""); return 0; }
    SnowPlayerStateV1 player = {0}; player.struct_size = sizeof player;
    char why[160] = "";
    int rc = player_fill(&player, why, sizeof why);
    if (rc) { put(o, "\"error\":\"no_player\",\"detail\":"); put_str(o, why); return 0; }
    SnowAnimationChannelRaw channel = {0};
    rc = snow_adapter.animation_channel((uint32_t)r->channel_key, &channel, why, sizeof why);
    if (rc == 2) drop_binding(why);
    if (rc || channel.guards_matched != 1 || channel.found > 1) {
        put(o, "\"error\":\"animation_observation_refused\",\"detail\":"); put_str(o, why); return 0;
    }
    if (channel.found) for (int i = 0; i < 4; i++) {
        if (!isfinite(channel.vector[i]) || !isfinite(channel.rotation[i]) ||
            !isfinite(channel.parent_vector[i]) || !isfinite(channel.parent_rotation[i]) ||
            !isfinite(channel.provider_vector[i]) || !isfinite(channel.provider_rotation[i])) {
            put(o, "\"error\":\"invalid_animation_value\""); return 0;
        }
    }
    if (channel.found) for (int i=0;i<16;i++) if (!isfinite(channel.owner_matrix[i])) {
        put(o, "\"error\":\"invalid_animation_owner_value\""); return 0;
    }
    put(o, "\"identity\":%llu,\"key\":%llu,\"found\":%s,\"epoch\":%u,\"guards_matched\":true,"
           "\"atomic_snapshot\":false,\"lifetime_pinned\":false,\"animation_completion_established\":false,"
           "\"suitable_for_animation_writes\":false,\"adapter\":",
        (unsigned long long)player.identity, (unsigned long long)r->channel_key,
        channel.found ? "true" : "false", channel.epoch);
    put_str(o, snow_adapter.name);
    if (channel.found) put(o, ",\"vector\":[%.9g,%.9g,%.9g,%.9g],\"rotation\":[%.9g,%.9g,%.9g,%.9g]",
        channel.vector[0],channel.vector[1],channel.vector[2],channel.vector[3],
        channel.rotation[0],channel.rotation[1],channel.rotation[2],channel.rotation[3]);
    if (channel.found) {
        put(o, ",\"record_index\":%u,\"bank_flags\":%u,\"conversion_direct\":%s,"
               "\"coordinate_space_semantics\":\"native_provider_conversion_only\"",
            channel.record_index,channel.bank_flags,(channel.bank_flags&(1u<<26))?"true":"false");
        put(o, ",\"owner_accessor_present\":%s,\"owner_reader_word\":%u,"
               "\"owner_transform_freshness_established\":false,\"owner_matrix\":[",
            channel.owner_accessor_present?"true":"false",channel.owner_reader_word);
        for(int i=0;i<16;i++) put(o,"%s%.9g",i?",":"",channel.owner_matrix[i]);
        put(o,"]");
        const char *names[]={"parent_vector","parent_rotation","provider_vector","provider_rotation"};
        const float *values[]={channel.parent_vector,channel.parent_rotation,channel.provider_vector,channel.provider_rotation};
        for (int i=0;i<4;i++) put(o, ",\"%s\":[%.9g,%.9g,%.9g,%.9g]",names[i],values[i][0],values[i][1],values[i][2],values[i][3]);
    }
    return 1;
}

static double ms_since(LARGE_INTEGER t0) {
    LARGE_INTEGER t; QueryPerformanceCounter(&t);
    return (double)(t.QuadPart - t0.QuadPart) * 1000.0 / (double)qpf.QuadPart;
}

static int read_now(SnowCounters *c, Out *err) {
    char why[160];
    if (snow_adapter.read(c, why, sizeof why) == 0) return 1;
    put(err, "\"error\":\"read_failed\",\"detail\":"); put_str(err, why);
    return 0;
}

/* Wait until EndFrame has run at least `frames` further requests. */
static int wait_frames(SnowCounters *c, uint32_t from, uint32_t frames, DWORD ms) {
    ULONGLONG end = GetTickCount64() + ms;
    char why[160];
    while (GetTickCount64() < end) {
        if (snow_adapter.read(c, why, sizeof why)) return 0;
        if (c->end_frame - from >= frames) return 1;
        Sleep(1);
    }
    return 0;
}

static void put_counters(Out *o, const char *name, const SnowCounters *c) {
    put(o, "\"%s\":{\"group\":", name); put_group(o, c->group);
    put(o, ",\"held\":%s,\"step\":%u,\"paused_job\":%u,\"end_frame\":%u}",
        SNOW_GROUP_HELD(c->group) ? "true" : "false", c->step, c->paused, c->end_frame);
}

static int do_status(Out *o) {
    SnowCounters c;
    put(o, "\"host_version\":\"%s\",\"api_version\":%d,\"adapter\":", HOST_VERSION, API_VERSION);
    put_str(o, snow_adapter.name);
    put(o, ",\"bound\":%s,\"uptime_ms\":%llu,\"host_paused\":%s,\"faulted\":%s,\"commands_completed\":%lld,\"commands_failed\":%lld",
        bound ? "true" : "false", GetTickCount64() - start_tick, host_paused ? "true" : "false",
        faulted ? "true" : "false", commands_completed, commands_failed);
    put(o, ",\"ready\":%s,\"plugins_initialized\":%s,\"plugins_active\":%d,\"steps_released\":%llu",
        engine_ready && plugins_initialized ? "true" : "false", plugins_initialized ? "true" : "false",
        snow_plugins_active(), (unsigned long long)steps_released);
    put(o, ",\"player_bound\":%s", player_bound ? "true" : "false");
    if (host_paused) put(o, ",\"lease_ms\":%lu,\"lease_remaining_ms\":%lld", lease_ms, (long long)(lease_deadline - GetTickCount64()));
    if (last_recovery[0]) { put(o, ",\"last_recovery\":"); put_str(o, last_recovery); }
    if (!bound) { put(o, ",\"bind_error\":"); put_str(o, bind_why); return 1; }
    char why[160];
    if (snow_adapter.read(&c, why, sizeof why)) { put(o, ",\"read_error\":"); put_str(o, why); return 1; }
    put(o, ","); put_counters(o, "engine", &c);
    put(o, ",\"ordinary\":%s", SNOW_GROUP_ORDINARY(c.group) ? "true" : "false");
    return 1;
}

static int do_pause(const Request *r, Out *o) {
    SnowCounters a, b;
    long long lease = r->has_lease ? r->lease_ms : DEFAULT_LEASE_MS;
    if (lease < 1000 || lease > MAX_LEASE_MS) { put(o, "\"error\":\"bad_params\",\"detail\":\"lease_ms must be 1000..%d\"", MAX_LEASE_MS); return 0; }
    if (!read_now(&a, o)) return 0;
    if (host_paused && SNOW_GROUP_HELD(a.group) && a.owner == pause_owner) {
        lease_ms = (DWORD)lease;
        put(o, "\"already_held_by_host\":true,"); put_counters(o, "engine", &a);
        return 1;
    }
    if (!SNOW_GROUP_ORDINARY(a.group)) { put(o, "\"error\":\"not_ordinary\",\"group\":"); put_group(o, a.group); return 0; }
    /* Step must be advancing before we claim to have paused it. */
    if (!wait_frames(&b, a.end_frame, 3, 1000) || b.step == a.step) { put(o, "\"error\":\"step_not_advancing\""); return 0; }
    pause_baseline = b.group; pause_owner = b.owner;
    snow_adapter.enter();
    host_paused = 1; lease_ms = (DWORD)lease; /* claim first so the lease can recover a partial enter */
    SnowCounters h1, h2;
    if (!wait_frames(&h1, b.end_frame, 2, 1000) || !SNOW_GROUP_HELD(h1.group) ||
        !wait_frames(&h2, h1.end_frame, 3, 1000) || h2.step != h1.step) {
        put(o, "\"error\":\"hold_not_verified\"");
        return 0; /* host_paused stays set; the client should resume, or the lease will */
    }
    snow_plugins_on_pause();
    put(o, "\"baseline_group\":"); put_group(o, pause_baseline);
    put(o, ",\"lease_ms\":%lu,", lease_ms); put_counters(o, "engine", &h2);
    return 1;
}

/* Leave stop mode through the engine's clear routine; restore the recorded
 * baseline group by compare-and-swap only if the routine did not. */
static int release_hold(Out *o, const char *reason) {
    SnowCounters a, b, c;
    if (!read_now(&a, o)) return 0;
    if (a.owner != pause_owner) { put(o, "\"error\":\"owner_changed\""); host_paused = 0; return 0; }
    /* Never run the clear routine outside stop mode (for example after a partial enter). */
    if (!SNOW_GROUP_ORDINARY(a.group)) snow_adapter.leave();
    int fallback = 0;
    if (!wait_frames(&b, a.end_frame, 2, 1000) || !SNOW_GROUP_ORDINARY(b.group)) {
        uint32_t seen;
        if (!read_now(&b, o)) return 0;
        if (snow_adapter.cas_group(b.owner, b.group, pause_baseline, &seen)) {
            put(o, "\"error\":\"restore_failed\",\"group\":"); put_group(o, seen); return 0;
        }
        fallback = 1;
    }
    if (!wait_frames(&c, b.end_frame, 3, 1000) || c.step == b.step) {
        put(o, "\"error\":\"step_not_resumed\",\"fallback\":%s", fallback ? "true" : "false"); return 0;
    }
    host_paused = 0;
    if (reason) snprintf(last_recovery, sizeof last_recovery, "%s", reason);
    snow_plugins_on_resume(!reason ? SNOW_RESUME_REQUESTED :
                           !strcmp(reason, "lease_expired") ? SNOW_RESUME_LEASE_EXPIRED : SNOW_RESUME_CLIENT_DISCONNECTED);
    put(o, "\"fallback_restore\":%s,", fallback ? "true" : "false"); put_counters(o, "engine", &c);
    return 1;
}

static int do_resume(Out *o) {
    if (!host_paused) { put(o, "\"error\":\"not_paused_by_host\""); return 0; }
    return release_hold(o, NULL);
}

/* One world step = one execution of the world Step job (one engine request).
 * It is neither a rendered frame nor a physics substep. Method validated
 * cross-process: clear the group, wait for Step to start, re-arm immediately. */
static int do_step(const Request *r, Out *o) {
    long long count = r->has_count ? r->count : 1;
    if (count < 1 || count > MAX_STEPS) { put(o, "\"error\":\"bad_params\",\"detail\":\"count must be 1..%d\"", MAX_STEPS); return 0; }
    if (!host_paused) { put(o, "\"error\":\"not_paused_by_host\""); return 0; }
    SnowCounters first;
    if (!read_now(&first, o)) return 0;
    if (!SNOW_GROUP_HELD(first.group) || first.owner != pause_owner) { put(o, "\"error\":\"not_held\""); return 0; }
    uint32_t held = first.group, cleared = held & 0xff000000u;
    int exact = 0; double max_release = 0;
    put(o, "\"unit\":\"world_step_job\",\"verification\":\"request_token_stable_after_rearm\",\"execution_count_verified\":false,\"steps\":[");
    long long n;
    for (n = 0; n < count; n++) {
        SnowCounters a, b, after; uint32_t seen;
        if (!read_now(&a, o)) break;
        if (!wait_frames(&b, a.end_frame, 2, 1000) || b.step != a.step) { put(o, "],\"error\":\"step_not_frozen\""); goto partial; }
        LARGE_INTEGER t0; QueryPerformanceCounter(&t0);
        if (snow_adapter.cas_group(b.owner, held, cleared, &seen)) { put(o, "],\"error\":\"group_changed\",\"group\":"); put_group(o, seen); goto partial; }
        uint32_t released = b.step; char why[160]; int ok = 0;
        while (ms_since(t0) < STEP_TIMEOUT_MS) {
            SnowCounters s;
            if (snow_adapter.read(&s, why, sizeof why)) break;
            if (s.step != b.step) { released = s.step; ok = 1; break; }
            YieldProcessor();
        }
        double release_ms = ms_since(t0);
        if (snow_adapter.cas_group(b.owner, cleared, held, &seen)) { put(o, "],\"error\":\"rearm_failed\",\"group\":"); put_group(o, seen); goto partial; }
        if (!ok) { put(o, "],\"error\":\"step_timeout\""); goto partial; }
        if (!wait_frames(&after, b.end_frame, 4, 1000)) { put(o, "],\"error\":\"frames_stalled\""); goto partial; }
        LARGE_INTEGER verified; QueryPerformanceCounter(&verified);
        int one = snow_step_release_stable(b.step, released, after.step, SNOW_GROUP_HELD(after.group));
        exact += one; if (release_ms > max_release) max_release = release_ms;
        put(o, "%s{\"step_before\":%u,\"step_released\":%u,\"step_after\":%u,\"end_frame_after\":%u,\"release_ms\":%.3f,\"exactly_one\":%s,\"release_begin_qpc\":%llu,\"rearm_verified_qpc\":%llu,\"qpc_frequency\":%llu}",
            n ? "," : "", b.step, released, after.step, after.end_frame, release_ms, one ? "true" : "false",
            (unsigned long long)t0.QuadPart, (unsigned long long)verified.QuadPart, (unsigned long long)qpf.QuadPart);
        if (!one) { n++; put(o, "],\"error\":\"not_exactly_one\""); goto partial; }
        /* Observed release boundary: Step request token changed and hold is re-armed.
         * Exact execution count needs an independent callback recorder. */
        steps_released++;
        SnowStepInfoV1 info = {sizeof info, (uint32_t)n, (uint32_t)count, 0, steps_released, release_ms};
        snow_plugins_on_step(&info);
    }
    put(o, "],\"requested\":%lld,\"completed\":%lld,\"exactly_one\":%d,\"max_release_ms\":%.3f", count, n, exact, max_release);
    return 1;
partial:
    put(o, ",\"requested\":%lld,\"completed\":%lld,\"exactly_one\":%d", count, n, exact);
    return 0;
}

static void execute(const Request *r, Out *o) {
    int ok = 0;
    put(o, "{\"id\":%lld,\"result\":{", r->id);
    if (!strcmp(r->method, "host.hello") || !strcmp(r->method, "simulation.status") || !strcmp(r->method, "host.heartbeat"))
        ok = do_status(o);
    else if (!strcmp(r->method, "plugins.list")) {
        char list[MAX_REPLY / 2];
        snow_plugins_describe(list, sizeof list);
        put(o, "\"plugins\":%s", list); ok = 1;
    } else if (!strcmp(r->method, "_disconnect")) {
        ok = 1;
        if (host_paused) { ok = release_hold(o, "client_disconnected"); host_log("recovery", "client disconnected while paused: %s", ok ? "resumed" : "FAILED"); }
    } else if (!bound || !engine_ready || !plugins_initialized) put(o, "\"error\":\"adapter_unavailable\",\"detail\":"), put_str(o, bind_why);
    else if (faulted) put(o, "\"error\":\"host_faulted\"");
    else if (!strcmp(r->method, "simulation.pause")) ok = do_pause(r, o);
    else if (!strcmp(r->method, "simulation.resume")) ok = do_resume(o);
    else if (!strcmp(r->method, "simulation.step_world")) ok = do_step(r, o);
    else if (!strcmp(r->method, "player.bind")) ok = do_player_bind(r, o);
    else if (!strcmp(r->method, "animation.get_cached_parent")) ok = do_cached_parent(o);
    else if (!strcmp(r->method, "animation.get_channel")) ok = do_animation_channel(r, o);
    else if (!strcmp(r->method, "player.get")) ok = do_player_get(o);
    else if (!strcmp(r->method, "player.set_velocity")) ok = do_player_set_velocity(r, o);
    else if (!strcmp(r->method, "player.adjust_speed")) ok = do_player_adjust_speed(r, o);
    else if (!strcmp(r->method, "player.set_position")) ok = do_player_set_position(r, o);
    put(o, "},\"status\":\"%s\"}\n", ok ? "completed" : "failed");
    if (ok) commands_completed++; else commands_failed++;
    if (host_paused) lease_deadline = GetTickCount64() + lease_ms;
    reply_ok = ok;
}

/* Startup may precede engine initialization. Retry read-only identity/readiness
 * checks on the executor; never weaken signatures or enable writes while waiting. */
static void startup_tick(void) {
    if (engine_ready && plugins_initialized) return;
    char why[160] = "";
    if (!bound) {
        if (snow_adapter.bind(why, sizeof why)) goto waiting;
        bound = 1;
        host_log("host", "adapter identity verified; waiting for engine owner");
    }
    SnowCounters c;
    if (snow_adapter.read(&c, why, sizeof why)) goto waiting;
    engine_ready = 1;
    bind_why[0] = 0;
    host_log("host", "engine ready; initializing plugins");
    host_log("host", "plugins: %d active", snow_plugins_init(dir));
    plugins_initialized = 1;
    write_marker("ready");
    return;
waiting:
    if (strcmp(why, bind_why)) {
        snprintf(bind_why, sizeof bind_why, "%s", why);
        host_log("startup", "waiting: %s", bind_why);
    }
}

static DWORD WINAPI executor(LPVOID unused) {
    (void)unused;
    /* Plugins load on the executor so every plugin call is serialized with commands. */
    startup_tick();
    int watching = snow_adapter.player_check || snow_adapter.player_acquire;
    for (;;) {
        DWORD wait = watching || !plugins_initialized ? WATCH_MS : INFINITE;
        if (host_paused) {
            ULONGLONG now = GetTickCount64();
            DWORD left = lease_deadline > now ? (DWORD)(lease_deadline - now) : 0;
            if (left < wait) wait = left;
        }
        if (WaitForSingleObject(work_ev, wait) == WAIT_TIMEOUT) {
            if (!host_paused || GetTickCount64() < lease_deadline) { startup_tick(); if (plugins_initialized) watch_tick(); continue; }
            char buf[1024]; Out o = {buf, sizeof buf, 0};
            int ok = release_hold(&o, "lease_expired");
            host_log("recovery", "lease expired; resume %s: %s", ok ? "ok" : "FAILED", buf);
            if (!ok) { faulted = 1; host_paused = 0; } /* stop retrying; status reports the fault */
            continue;
        }
        Out o = {reply, sizeof reply, 0};
        startup_tick();
        execute(&pending, &o);
        host_log("exec", "%.*s", (int)(o.len > 300 ? 300 : o.len - 1), reply);
        SetEvent(done_ev);
        flush_events();
    }
    return 0;
}

/* ---------- io thread: parsing and transport only ---------- */

static int send_all(SOCKET s, const char *p, size_t n) {
    while (n) { int k = send(s, p, (int)n, 0); if (k <= 0) return 0; p += k; n -= k; }
    return 1;
}
static void send_line(SOCKET s, long long id, const char *status, const char *error) {
    char b[256];
    int n = snprintf(b, sizeof b, "{\"id\":%lld,\"status\":\"%s\"%s%s%s}\n", id, status,
                     error ? ",\"error\":\"" : "", error ? error : "", error ? "\"" : "");
    send_all(s, b, n);
}
static int known(const char *m) {
    static const char *methods[] = {"host.hello", "host.heartbeat", "simulation.status", "simulation.pause",
                                    "simulation.resume", "simulation.step_world", "plugins.list",
                                    "player.bind", "player.get", "player.set_velocity",
                                    "player.set_position", "player.adjust_speed", "animation.get_channel", "animation.get_cached_parent"};
    for (size_t i = 0; i < sizeof methods / sizeof *methods; i++) if (!strcmp(m, methods[i])) return 1;
    return 0;
}
static int run_command(const Request *r, DWORD timeout) {
    pending = *r;
    SetEvent(work_ev);
    return WaitForSingleObject(done_ev, timeout) == WAIT_OBJECT_0;
}

static void serve(SOCKET c) {
    char buf[MAX_LINE + 1]; size_t len = 0;
    for (;;) {
        int k = recv(c, buf + len, (int)(MAX_LINE - len), 0);
        if (k <= 0) break;
        len += k;
        char *nl;
        while ((nl = memchr(buf, '\n', len))) {
            *nl = 0;
            Request r;
            if (!parse_request(buf, &r)) send_line(c, r.has_id ? r.id : -1, "rejected", "malformed_request");
            else if (!known(r.method)) send_line(c, r.id, "rejected", "unknown_method");
            else {
                send_line(c, r.id, "accepted", NULL);
                DWORD timeout = 15000 + (r.has_count && r.count > 0 && r.count <= MAX_STEPS ? (DWORD)r.count * 3000 : 3000);
                if (!run_command(&r, timeout)) {
                    /* The executor is wedged. Report it and stop serving commands. */
                    host_log("io", "executor timeout on %s", r.method);
                    send_line(c, r.id, "failed", "executor_timeout");
                    faulted = 1;
                    return;
                }
                if (!send_all(c, reply, strlen(reply))) return;
            }
            len -= (nl + 1 - buf);
            memmove(buf, nl + 1, len);
        }
        if (len == MAX_LINE) { send_line(c, -1, "rejected", "line_too_long"); break; }
    }
}

static DWORD WINAPI io_thread(LPVOID unused) {
    (void)unused;
    WSADATA w;
    if (WSAStartup(MAKEWORD(2, 2), &w)) { host_log("io", "WSAStartup failed"); write_marker("socket_failed"); return 1; }
    SOCKET l = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET; a.sin_port = htons(port); a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    BOOL excl = TRUE;
    setsockopt(l, SOL_SOCKET, SO_EXCLUSIVEADDRUSE, (const char *)&excl, sizeof excl);
    if (l == INVALID_SOCKET || bind(l, (struct sockaddr *)&a, sizeof a) || listen(l, 2)) {
        host_log("io", "listen on 127.0.0.1:%u failed: %d", port, WSAGetLastError());
        write_marker("listen_failed");
        return 1;
    }
    host_log("io", "listening on 127.0.0.1:%u", port);
    write_marker("listening");
    for (;;) {
        SOCKET c = accept(l, NULL, NULL);
        if (c == INVALID_SOCKET) { Sleep(100); continue; }
        host_log("io", "client connected");
        serve(c);
        closesocket(c);
        host_log("io", "client disconnected");
        if (!faulted) { Request d = {0}; d.id = -1; strcpy(d.method, "_disconnect"); run_command(&d, 15000); }
    }
}

/* ---------- entry points ---------- */

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID unused) {
    (void)unused;
    if (reason == DLL_PROCESS_ATTACH) { self = h; DisableThreadLibraryCalls(h); }
    return TRUE;
}

/* Run once on its own thread after loading. Low 16 bits of param: TCP port
 * (0 = default). Returns 0 when both threads started, 1 if already started. */
__declspec(dllexport) DWORD WINAPI SnowHost_Start(LPVOID param) {
    if (InterlockedCompareExchange(&started, 1, 0)) return 1;
    port = (unsigned short)((uintptr_t)param & 0xffff);
    if (!port) port = DEFAULT_PORT;
    DWORD n = GetModuleFileNameW(self, dir, MAX_PATH);
    if (!n || n >= MAX_PATH) return 2;
    while (n && dir[n - 1] != L'\\') n--;
    dir[n ? n - 1 : 0] = 0;
    InitializeCriticalSection(&log_lock);
    QueryPerformanceFrequency(&qpf);
    start_tick = GetTickCount64();
    snprintf(bind_why, sizeof bind_why, "engine initialization pending");
    host_log("host", "v%s api %d adapter %s: deferred binding", HOST_VERSION, API_VERSION, snow_adapter.name);
    work_ev = CreateEventW(NULL, FALSE, FALSE, NULL);
    done_ev = CreateEventW(NULL, FALSE, FALSE, NULL);
    if (!work_ev || !done_ev) return 3;
    HANDLE e = CreateThread(NULL, 0, executor, NULL, 0, NULL);
    if (!e) return 4;
    CloseHandle(e);
    HANDLE t = CreateThread(NULL, 0, io_thread, NULL, 0, NULL);
    if (!t) return 5;
    CloseHandle(t);
    write_marker("starting");
    return 0;
}
