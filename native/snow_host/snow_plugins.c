/* Plugin manager for the Snow mod host (API v1, see snow_plugin.h).
 *
 * Called only from the host executor thread. Every call into plugin code is
 * handed to a dedicated plugin thread and awaited with a time budget, so a
 * slow or crashing plugin cannot stall or kill the executor:
 *   - timeout: the plugin is disabled and the thread abandoned; a fresh plugin
 *     thread serves the remaining plugins.
 *   - fatal exception on a plugin thread: a vectored handler scoped to plugin
 *     threads moves that thread onto a private emergency stack, where it reports
 *     the fault and exits. The plugin is disabled.
 * Containment is best-effort. A plugin that faults while holding a lock shared
 * with the game (for example the process heap) can still deadlock the process.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "snow_plugins.h"

#define MAX_PLUGINS 16
#define INIT_BUDGET_MS 1000
#define EMERGENCY_STACK (64 * 1024)
#define MAX_THREADS 32

enum { P_ACTIVE, P_DISABLED, P_FAULTED, P_REJECTED };
static const char *state_names[] = {"active", "disabled", "faulted", "rejected"};
enum { J_INIT, J_PAUSE, J_STEP, J_RESUME, J_UNLOAD, J_PLAYER };
/* Smallest SnowPluginV1 accepted (host 0.2 layout, ending at on_unload) and the size that includes on_player. */
#define PLUGIN_V1_MIN (offsetof(SnowPluginV1, on_unload) + sizeof(void (*)(void)))
#define PLUGIN_HAS_ON_PLAYER (offsetof(SnowPluginV1, on_player) + sizeof(void (*)(void)))

typedef struct Plugin {
    WCHAR file[MAX_PATH];
    char file_utf8[MAX_PATH], config_utf8[MAX_PATH * 3], reason[96];
    char name[48], version[48]; /* copies: plugin strings die with FreeLibrary */
    HMODULE module;
    SnowModInitializeFn init;
    SnowHostApiV1 api;
    SnowPluginV1 desc;
    int state;
    long long calls;
} Plugin;

typedef struct Job {
    int kind, rc;
    DWORD fault;
    Plugin *p;
    SnowStepInfoV1 step;          /* copied: plugin code never sees executor memory */
    SnowResumeReason reason;
    SnowPlayerEventV1 event;
} Job;

/* Each plugin thread owns its Job slot. The executor copies arguments in and
 * results out, so an abandoned thread that wakes late writes only to its own slot. */
typedef struct Worker {
    HANDLE thread, job_ev, done_ev;
    DWORD tid;
    Job job;
    BYTE *stack;
} Worker;

static Plugin plugins[MAX_PLUGINS];
static int plugin_count;
static Worker *worker;
static volatile DWORD plugin_tids[MAX_THREADS];
static Worker *volatile plugin_workers[MAX_THREADS];
static volatile LONG thread_slots;

static void run_job(Job *j) {
    SnowPluginV1 *d = &j->p->desc;
    switch (j->kind) {
    case J_INIT: j->rc = j->p->init(&j->p->api, d); break;
    case J_PAUSE: j->rc = d->on_pause ? d->on_pause(d->user) : 0; break;
    case J_STEP: j->rc = d->on_step ? d->on_step(d->user, &j->step) : 0; break;
    case J_RESUME: j->rc = d->on_resume ? d->on_resume(d->user, j->reason) : 0; break;
    case J_UNLOAD: if (d->on_unload) d->on_unload(d->user); j->rc = 0; break;
    case J_PLAYER: j->rc = d->struct_size >= PLUGIN_HAS_ON_PLAYER && d->on_player ? d->on_player(d->user, &j->event) : 0; break;
    }
}

static DWORD WINAPI worker_main(LPVOID arg) {
    Worker *w = arg;
    for (;;) {
        WaitForSingleObject(w->job_ev, INFINITE);
        run_job(&w->job);
        SetEvent(w->done_ev);
    }
    return 0;
}

/* Entered on the emergency stack after a fatal exception in plugin code. */
static void __attribute__((noreturn)) worker_abort(Worker *w, DWORD code) {
    w->job.fault = code ? code : 1;
    SetEvent(w->done_ev);
    ExitThread(code);
}

static int fatal(DWORD code) {
    switch (code) {
    case EXCEPTION_ACCESS_VIOLATION: case EXCEPTION_ILLEGAL_INSTRUCTION: case EXCEPTION_PRIV_INSTRUCTION:
    case EXCEPTION_INT_DIVIDE_BY_ZERO: case EXCEPTION_INT_OVERFLOW: case EXCEPTION_STACK_OVERFLOW:
    case EXCEPTION_ARRAY_BOUNDS_EXCEEDED: case EXCEPTION_IN_PAGE_ERROR:
        return 1;
    }
    return 0;
}

static LONG CALLBACK plugin_veh(PEXCEPTION_POINTERS e) {
    DWORD code = e->ExceptionRecord->ExceptionCode, tid = GetCurrentThreadId();
    if (!fatal(code)) return EXCEPTION_CONTINUE_SEARCH;
    LONG n = thread_slots;
    for (LONG i = 0; i < n && i < MAX_THREADS; i++) {
        if (plugin_tids[i] != tid) continue;
        Worker *w = plugin_workers[i];
        /* x64 entry convention: rsp % 16 == 8, with 32 bytes of shadow space above the return slot. */
        DWORD64 top = ((DWORD64)(w->stack + EMERGENCY_STACK)) & ~(DWORD64)15;
        e->ContextRecord->Rsp = top - 0x28;
        e->ContextRecord->Rip = (DWORD64)worker_abort;
        e->ContextRecord->Rcx = (DWORD64)w;
        e->ContextRecord->Rdx = code;
        return EXCEPTION_CONTINUE_EXECUTION;
    }
    return EXCEPTION_CONTINUE_SEARCH;
}

static Worker *new_worker(void) {
    if (thread_slots >= MAX_THREADS) return NULL;
    Worker *w = calloc(1, sizeof *w);
    if (!w) return NULL;
    w->job_ev = CreateEventW(NULL, FALSE, FALSE, NULL);
    w->done_ev = CreateEventW(NULL, FALSE, FALSE, NULL);
    w->stack = VirtualAlloc(NULL, EMERGENCY_STACK, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!w->job_ev || !w->done_ev || !w->stack) return NULL;
    w->thread = CreateThread(NULL, 0, worker_main, w, CREATE_SUSPENDED, &w->tid);
    if (!w->thread) return NULL;
    LONG slot = thread_slots;
    plugin_workers[slot] = w; plugin_tids[slot] = w->tid;
    InterlockedIncrement(&thread_slots);
    ResumeThread(w->thread);
    return w;
}

static void disable(Plugin *p, int state, const char *fmt, ...) {
    va_list ap; va_start(ap, fmt);
    vsnprintf(p->reason, sizeof p->reason, fmt, ap);
    va_end(ap);
    p->state = state;
    snow_host_log("plugin", "%s %s: %s", p->name[0] ? p->name : p->file_utf8, state_names[state], p->reason);
}

/* Returns the job result, or -1 after disabling the plugin for a timeout or fault. */
static int call(Plugin *p, Job *j, DWORD budget) {
    if (!worker && !(worker = new_worker())) { disable(p, P_FAULTED, "no plugin thread"); return -1; }
    j->p = p; j->fault = 0; j->rc = 0;
    worker->job = *j;
    p->calls++;
    SetEvent(worker->job_ev);
    if (WaitForSingleObject(worker->done_ev, budget) != WAIT_OBJECT_0) {
        /* Abandon this thread with its Worker (leaked on purpose). */
        worker = NULL;
        disable(p, P_FAULTED, "call exceeded %lu ms budget", budget);
        return -1;
    }
    *j = worker->job;
    if (j->fault) {
        CloseHandle(worker->thread);
        worker = NULL; /* that thread has exited */
        disable(p, P_FAULTED, "exception 0x%08lx", j->fault);
        return -1;
    }
    return j->rc;
}

/* A plugin that returns nonzero is disabled cleanly: on_unload, then FreeLibrary. */
static void after(Plugin *p, int rc, const char *what) {
    if (rc <= 0) return;
    disable(p, P_DISABLED, "%s returned %d", what, rc);
    Job u = {.kind = J_UNLOAD};
    if (call(p, &u, SNOW_PLUGIN_CALL_BUDGET_MS) == 0) FreeLibrary(p->module);
}

static int valid_name(const char *s);

static void api_log(void *ctx, const char *message) {
    Plugin *p = ctx;
    /* Called by the plugin itself, so its own strings are still mapped (matters during Initialize). */
    const char *tag = p->name[0] ? p->name : valid_name(p->desc.name) ? p->desc.name : p->file_utf8;
    snow_host_log("plugin", "%s: %.400s", tag, message ? message : "");
}

static int api_state(void *ctx, SnowHostStateV1 *out) {
    (void)ctx;
    if (!out || out->struct_size < sizeof *out) return 1;
    snow_host_state(out);
    return 0;
}

static int api_player(void *ctx, SnowPlayerStateV1 *out) {
    (void)ctx;
    if (!out || out->struct_size < sizeof *out) return SNOW_E_BAD_ARGS;
    return snow_host_player(out);
}

static int api_set_velocity(void *ctx, const float velocity[3]) {
    (void)ctx;
    if (!velocity) return SNOW_E_BAD_ARGS;
    return snow_host_set_velocity(velocity);
}

static int api_set_pose(void *ctx, const SnowPlayerStateV1 *target) {
    (void)ctx;
    if (!target || target->struct_size < sizeof *target) return SNOW_E_BAD_ARGS;
    return snow_host_set_pose(target);
}

static int valid_name(const char *s) {
    if (!s || !*s || strlen(s) > 47) return 0;
    for (; *s; s++) if ((unsigned char)*s < 0x21 || *s == '"' || *s == '\\' || (unsigned char)*s > 0x7e) return 0;
    return 1;
}

int snow_plugins_init(const WCHAR *dir) {
    AddVectoredExceptionHandler(1, plugin_veh);
    WCHAR pattern[MAX_PATH];
    if (_snwprintf(pattern, MAX_PATH, L"%ls\\plugins\\*.dll", dir) < 0) return 0;
    WIN32_FIND_DATAW f;
    HANDLE h = FindFirstFileW(pattern, &f);
    if (h == INVALID_HANDLE_VALUE) { snow_host_log("plugin", "no plugins folder entries"); return 0; }
    do {
        if (plugin_count == MAX_PLUGINS) { snow_host_log("plugin", "more than %d plugins; rest ignored", MAX_PLUGINS); break; }
        Plugin *p = &plugins[plugin_count++];
        _snwprintf(p->file, MAX_PATH, L"%ls\\plugins\\%ls", dir, f.cFileName);
        WideCharToMultiByte(CP_UTF8, 0, f.cFileName, -1, p->file_utf8, sizeof p->file_utf8, NULL, NULL);
        WCHAR cfg[MAX_PATH];
        size_t len = wcslen(p->file);
        _snwprintf(cfg, MAX_PATH, L"%.*ls.ini", (int)(len - 4), p->file);
        WideCharToMultiByte(CP_UTF8, 0, cfg, -1, p->config_utf8, sizeof p->config_utf8, NULL, NULL);
        /* Loaded on the executor: DllMain runs under the loader lock and is not contained. */
        p->module = LoadLibraryW(p->file);
        if (!p->module) { disable(p, P_REJECTED, "LoadLibrary error %lu", GetLastError()); continue; }
        p->init = (SnowModInitializeFn)(void (*)(void))GetProcAddress(p->module, "SnowMod_Initialize");
        if (!p->init) { disable(p, P_REJECTED, "no SnowMod_Initialize export"); FreeLibrary(p->module); continue; }
        p->api = (SnowHostApiV1){sizeof(SnowHostApiV1), SNOW_PLUGIN_API_VERSION, SNOW_HOST_VERSION, p,
                                 api_log, p->config_utf8, api_state, api_player, api_set_velocity, api_set_pose};
        Job j = {.kind = J_INIT};
        int rc = call(p, &j, INIT_BUDGET_MS);
        if (rc < 0) continue; /* faulted; never unloaded */
        if (rc) { disable(p, P_REJECTED, "SnowMod_Initialize returned %d", rc); FreeLibrary(p->module); continue; }
        if (p->desc.api_version != SNOW_PLUGIN_API_VERSION || p->desc.struct_size < PLUGIN_V1_MIN) {
            disable(p, P_REJECTED, "api_version %u / struct_size %u unsupported", p->desc.api_version, p->desc.struct_size);
            continue; /* initialized code may hold state; leave it loaded but never call it */
        }
        if (!valid_name(p->desc.name)) { disable(p, P_REJECTED, "missing or invalid name"); continue; }
        snprintf(p->name, sizeof p->name, "%s", p->desc.name);
        snprintf(p->version, sizeof p->version, "%.47s", p->desc.version ? p->desc.version : "");
        for (char *c = p->version; *c; c++) if ((unsigned char)*c < 0x20 || (unsigned char)*c > 0x7e) *c = '?';
        p->state = P_ACTIVE;
        snow_host_log("plugin", "loaded %s %s from %s", p->name, p->version, p->file_utf8);
    } while (FindNextFileW(h, &f));
    FindClose(h);
    return snow_plugins_active();
}

int snow_plugins_active(void) {
    int n = 0;
    for (int i = 0; i < plugin_count; i++) n += plugins[i].state == P_ACTIVE;
    return n;
}

void snow_plugins_on_pause(void) {
    for (int i = 0; i < plugin_count; i++) {
        Plugin *p = &plugins[i];
        if (p->state != P_ACTIVE) continue;
        Job j = {.kind = J_PAUSE};
        after(p, call(p, &j, SNOW_PLUGIN_CALL_BUDGET_MS), "on_pause");
    }
}

void snow_plugins_on_step(const SnowStepInfoV1 *step) {
    for (int i = 0; i < plugin_count; i++) {
        Plugin *p = &plugins[i];
        if (p->state != P_ACTIVE) continue;
        Job j = {.kind = J_STEP, .step = *step};
        after(p, call(p, &j, SNOW_PLUGIN_CALL_BUDGET_MS), "on_step");
    }
}

void snow_plugins_on_resume(SnowResumeReason reason) {
    for (int i = 0; i < plugin_count; i++) {
        Plugin *p = &plugins[i];
        if (p->state != P_ACTIVE) continue;
        Job j = {.kind = J_RESUME, .reason = reason};
        after(p, call(p, &j, SNOW_PLUGIN_CALL_BUDGET_MS), "on_resume");
    }
}

void snow_plugins_on_player(const SnowPlayerEventV1 *event) {
    for (int i = 0; i < plugin_count; i++) {
        Plugin *p = &plugins[i];
        if (p->state != P_ACTIVE || p->desc.struct_size < PLUGIN_HAS_ON_PLAYER || !p->desc.on_player) continue;
        Job j = {.kind = J_PLAYER, .event = *event};
        after(p, call(p, &j, SNOW_PLUGIN_CALL_BUDGET_MS), "on_player");
    }
}

static void put_json_str(char *b, size_t n, size_t *len, const char *s) {
    if (*len < n) *len += snprintf(b + *len, n - *len, "\"");
    for (; s && *s && *len < n; s++)
        *len += snprintf(b + *len, n - *len, (*s == '"' || *s == '\\') ? "\\%c" : ((unsigned char)*s < 0x20 ? " " : "%c"), *s);
    if (*len < n) *len += snprintf(b + *len, n - *len, "\"");
}

size_t snow_plugins_describe(char *b, size_t n) {
    size_t len = 0;
    if (n) len += snprintf(b, n, "[");
    for (int i = 0; i < plugin_count && len < n; i++) {
        Plugin *p = &plugins[i];
        len += snprintf(b + len, n - len, "%s{\"file\":", i ? "," : "");
        put_json_str(b, n, &len, p->file_utf8);
        if (len < n) len += snprintf(b + len, n - len, ",\"name\":");
        put_json_str(b, n, &len, p->name);
        if (len < n) len += snprintf(b + len, n - len, ",\"version\":");
        put_json_str(b, n, &len, p->version);
        if (len < n) len += snprintf(b + len, n - len, ",\"state\":\"%s\",\"reason\":", state_names[p->state]);
        put_json_str(b, n, &len, p->reason);
        if (len < n) len += snprintf(b + len, n - len, ",\"calls\":%lld}", p->calls);
    }
    if (len < n) len += snprintf(b + len, n - len, "]");
    return len < n ? len : n - 1;
}
